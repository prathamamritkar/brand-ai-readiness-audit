#!/usr/bin/env python3

"""
Deterministic tests for Evidence Correlator.
"""

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from analyze_evidence import correlate  # noqa: E402


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(
            f"{message}\nExpected: {expected}\nActual: {actual}"
        )


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_empty_input():
    result = correlate({})

    assert_equal(
        result["schema_version"],
        "evidence-correlator/v1",
        "Schema version should be stable.",
    )

    assert_equal(
        result["findings"],
        [],
        "Empty input should produce no findings.",
    )

    assert_equal(
        result["summary"]["correlated_findings"],
        0,
        "Empty input should produce zero findings.",
    )

    assert_true(
        len(result["limitations"]) > 0,
        "Empty input should report a limitation.",
    )


def test_single_source():
    data = {
        "skills": {
            "engagement-audit": {
                "findings": [
                    {
                        "category": "cta",
                        "issue": "No primary CTA observed",
                        "status": "absent",
                        "page_url": "https://example.com/pricing",
                        "signal": "No primary CTA observed",
                        "source": "engagement audit",
                    }
                ]
            }
        }
    }

    result = correlate(data)

    assert_equal(
        len(result["findings"]),
        1,
        "Single observation should create one candidate.",
    )

    finding = result["findings"][0]

    assert_equal(
        finding["evidence_relationship"],
        "single_source",
        "One contributing skill should be single_source.",
    )

    assert_equal(
        finding["confidence"],
        "medium",
        "Concrete single-source evidence should have medium confidence.",
    )

    assert_equal(
        finding["evidence_sufficiency"],
        "sufficient",
        "Concrete page evidence should be sufficient.",
    )

    assert_equal(
        finding["affected_pages"],
        ["https://example.com/pricing"],
        "Page provenance should be preserved.",
    )


def test_corroborated_evidence():
    data = {
        "skills": {
            "machine-readability": {
                "findings": [
                    {
                        "category": "machine-readable structure",
                        "issue": "Structured content is weak",
                        "status": "absent",
                        "page_url": "https://example.com/product",
                        "signal": "Missing structured data",
                        "source": "machine readability",
                    }
                ]
            },
            "crawl-render-audit": {
                "findings": [
                    {
                        "category": "semantic structure",
                        "issue": "Machine structure is weak",
                        "status": "absent",
                        "page_url": "https://example.com/product",
                        "signal": "Missing semantic structure",
                        "source": "crawl render audit",
                    }
                ]
            },
        }
    }

    result = correlate(data)

    assert_equal(
        len(result["findings"]),
        1,
        "Compatible signals should be correlated.",
    )

    finding = result["findings"][0]

    assert_equal(
        finding["evidence_relationship"],
        "corroborated",
        "Independent supporting skills should produce corroborated evidence.",
    )

    assert_equal(
        finding["confidence"],
        "high",
        "Corroborated concrete evidence should have high confidence.",
    )

    assert_equal(
        set(finding["contributing_skills"]),
        {
            "machine-readability",
            "crawl-render-audit",
        },
        "All contributing skills must be preserved.",
    )


def test_conflicting_evidence():
    data = {
        "skills": {
            "freshness-corroboration": {
                "findings": [
                    {
                        "category": "freshness",
                        "issue": "Publication date",
                        "status": "present",
                        "page_url": "https://example.com/blog/post",
                        "signal": "Publication date is present",
                        "source": "structured date",
                    }
                ]
            },
            "crawl-render-audit": {
                "findings": [
                    {
                        "category": "freshness",
                        "issue": "Publication date",
                        "status": "absent",
                        "page_url": "https://example.com/blog/post",
                        "signal": "Publication date is absent",
                        "source": "visible evidence",
                    }
                ]
            },
        }
    }

    result = correlate(data)

    assert_equal(
        len(result["findings"]),
        1,
        "Conflicting signals about the same issue should remain one candidate.",
    )

    finding = result["findings"][0]

    assert_equal(
        finding["evidence_relationship"],
        "conflicting",
        "Opposing evidence should be marked conflicting.",
    )

    assert_equal(
        finding["confidence"],
        "low",
        "Conflicting evidence should have low confidence.",
    )

    assert_equal(
        len(finding["evidence"]),
        2,
        "Both sides of the conflict must be preserved.",
    )


def test_missing_skill_outputs():
    data = {
        "skills": {
            "engagement-audit": {
                "findings": [
                    {
                        "category": "cta",
                        "issue": "CTA absent",
                        "status": "absent",
                        "page_url": "https://example.com",
                        "signal": "No CTA observed",
                        "source": "engagement audit",
                    }
                ]
            }
        }
    }

    result = correlate(data)

    assert_true(
        any(
            "machine-readability" in limitation
            for limitation in result["limitations"]
        ),
        "Missing specialized skills should be reported.",
    )

    assert_equal(
        len(result["findings"]),
        1,
        "Available evidence should still be processed.",
    )


def test_uncertain_evidence():
    data = {
        "skills": {
            "crawl-render-audit": {
                "findings": [
                    {
                        "category": "rendering",
                        "issue": "Rendering could not be determined",
                        "status": "unable_to_determine",
                        "page_url": "https://example.com",
                        "signal": "Rendering behavior cannot be determined",
                        "source": "crawl render audit",
                    }
                ]
            }
        }
    }

    result = correlate(data)

    assert_equal(
        len(result["findings"]),
        1,
        "Uncertain evidence should remain traceable.",
    )

    finding = result["findings"][0]

    assert_equal(
        finding["evidence_relationship"],
        "unable_to_determine",
        "Uncertain evidence should remain uncertain.",
    )

    assert_equal(
        finding["evidence_sufficiency"],
        "unable_to_determine",
        "Uncertain evidence cannot establish sufficiency.",
    )

    assert_equal(
        finding["confidence"],
        "low",
        "Uncertain evidence should have low confidence.",
    )


def test_deduplication():
    data = {
        "skills": {
            "engagement-audit": {
                "findings": [
                    {
                        "category": "cta",
                        "issue": "CTA absent",
                        "status": "absent",
                        "page_url": "https://example.com",
                        "signal": "No primary CTA observed",
                        "source": "engagement audit",
                    },
                    {
                        "category": "cta",
                        "issue": "CTA absent",
                        "status": "absent",
                        "page_url": "https://example.com",
                        "signal": "No primary CTA observed",
                        "source": "engagement audit",
                    },
                ]
            }
        }
    }

    result = correlate(data)

    assert_equal(
        len(result["findings"]),
        1,
        "Duplicate observations should not create duplicate findings.",
    )


def test_different_issues_same_page():
    data = {
        "skills": {
            "engagement-audit": {
                "findings": [
                    {
                        "category": "cta",
                        "issue": "CTA absent",
                        "status": "absent",
                        "page_url": "https://example.com",
                        "signal": "No primary CTA observed",
                        "source": "engagement audit",
                    },
                    {
                        "category": "navigation",
                        "issue": "Navigation weak",
                        "status": "absent",
                        "page_url": "https://example.com",
                        "signal": "No contextual pathway observed",
                        "source": "engagement audit",
                    },
                ]
            }
        }
    }

    result = correlate(data)

    assert_equal(
        len(result["findings"]),
        2,
        "Different issues on the same page must remain separate.",
    )


def test_stable_output_order():
    data_a = {
        "skills": {
            "engagement-audit": {
                "findings": [
                    {
                        "category": "navigation",
                        "status": "absent",
                        "page_url": "https://example.com/b",
                        "signal": "No navigation pathway",
                        "source": "engagement",
                    },
                    {
                        "category": "cta",
                        "status": "absent",
                        "page_url": "https://example.com/a",
                        "signal": "No CTA",
                        "source": "engagement",
                    },
                ]
            }
        }
    }

    data_b = {
        "skills": {
            "engagement-audit": {
                "findings": [
                    {
                        "category": "cta",
                        "status": "absent",
                        "page_url": "https://example.com/a",
                        "signal": "No CTA",
                        "source": "engagement",
                    },
                    {
                        "category": "navigation",
                        "status": "absent",
                        "page_url": "https://example.com/b",
                        "signal": "No navigation pathway",
                        "source": "engagement",
                    },
                ]
            }
        }
    }

    result_a = correlate(data_a)
    result_b = correlate(data_b)

    assert_equal(
        json.dumps(result_a, sort_keys=True),
        json.dumps(result_b, sort_keys=True),
        "Equivalent inputs in different order should produce stable output.",
    )


def test_output_schema():
    data = {
        "skills": {
            "engagement-audit": {
                "findings": [
                    {
                        "category": "cta",
                        "status": "absent",
                        "page_url": "https://example.com",
                        "signal": "No CTA",
                        "source": "engagement audit",
                    }
                ]
            }
        }
    }

    result = correlate(data)

    required_top_level = {
        "schema_version",
        "summary",
        "findings",
        "limitations",
    }

    assert_equal(
        set(result.keys()),
        required_top_level,
        "Output should contain the required top-level fields.",
    )

    finding = result["findings"][0]

    required_finding_fields = {
        "candidate_id",
        "category",
        "issue",
        "scope",
        "affected_pages",
        "contributing_skills",
        "evidence_relationship",
        "evidence_sufficiency",
        "confidence",
        "evidence",
        "limitations",
    }

    assert_equal(
        set(finding.keys()),
        required_finding_fields,
        "Finding should contain the required fields.",
    )


def run_tests():
    tests = [
        test_empty_input,
        test_single_source,
        test_corroborated_evidence,
        test_conflicting_evidence,
        test_missing_skill_outputs,
        test_uncertain_evidence,
        test_deduplication,
        test_different_issues_same_page,
        test_stable_output_order,
        test_output_schema,
    ]

    passed = 0

    for test in tests:
        test()
        passed += 1
        print(f"PASS: {test.__name__}")

    print(f"\n{passed}/{len(tests)} tests passed.")


if __name__ == "__main__":
    run_tests()