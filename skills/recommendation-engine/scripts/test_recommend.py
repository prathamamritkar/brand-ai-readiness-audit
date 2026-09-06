"""
Deterministic tests for the Recommendation Engine.
"""

from __future__ import annotations

import json

from recommend import build_output


def run_test(name, condition):
    if not condition:
        raise AssertionError(f"FAIL: {name}")

    print(f"PASS: {name}")


def test_empty_input():
    output = build_output({})

    assert output["schema_version"] == "recommendation-engine/v1"
    assert output["summary"]["recommendations_generated"] == 0
    assert output["recommendations"] == []


def test_high_confidence_machine_structure():
    data = {
        "schema_version": "evidence-correlator/v1",
        "findings": [
            {
                "candidate_id": "candidate-machine-structure-example",
                "category": "machine_structure",
                "issue": "Machine-readable structure requires review",
                "scope": "page",
                "affected_pages": [
                    "https://example.com/product"
                ],
                "confidence": "high",
                "evidence_sufficiency": "sufficient",
                "evidence": [
                    {
                        "skill": "machine-readability",
                        "signal": "Missing structured data",
                        "status": "absent",
                    }
                ],
                "limitations": [],
            }
        ],
        "limitations": [],
    }

    output = build_output(data)

    assert output["summary"]["recommendations_generated"] == 1

    recommendation = output["recommendations"][0]

    assert recommendation["priority"] == "high"
    assert recommendation["confidence"] == "high"
    assert recommendation["evidence_sufficiency"] == "sufficient"
    assert recommendation["category"] == "machine_structure"
    assert recommendation["action"]
    assert recommendation["expected_outcome"]
    assert recommendation["verification"]


def test_medium_confidence_engagement():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-engagement-example",
                "category": "engagement_pathway",
                "issue": "Engagement pathways require review",
                "scope": "page",
                "affected_pages": [
                    "https://example.com/product"
                ],
                "confidence": "medium",
                "evidence_sufficiency": "sufficient",
                "evidence": [
                    {
                        "skill": "engagement-audit",
                        "signal": "No primary CTA observed",
                        "status": "absent",
                    }
                ],
            }
        ]
    }

    output = build_output(data)

    recommendation = output["recommendations"][0]

    assert recommendation["priority"] == "medium"
    assert recommendation["title"] == (
        "Clarify the primary engagement pathway"
    )


def test_low_confidence():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-low",
                "category": "navigation_pathway",
                "issue": "Navigation pathway may require review",
                "scope": "page",
                "confidence": "low",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
            }
        ]
    }

    output = build_output(data)

    recommendation = output["recommendations"][0]

    assert recommendation["priority"] == "low"
    assert recommendation["confidence"] == "low"


def test_insufficient_evidence_requires_verification():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-uncertain",
                "category": "freshness_signal",
                "issue": "Freshness signal requires review",
                "scope": "page",
                "confidence": "low",
                "evidence_sufficiency": "insufficient",
                "affected_pages": [
                    "https://example.com/blog"
                ],
                "evidence": [],
            }
        ]
    }

    output = build_output(data)

    recommendation = output["recommendations"][0]

    assert recommendation["priority"] == "low"
    assert recommendation["title"].startswith("Verify:")
    assert (
        recommendation["evidence_sufficiency"]
        == "insufficient"
    )
    assert recommendation["verification"]
    assert output["summary"]["verification_required"] == 1


def test_explicit_severity_is_preserved():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-explicit-high",
                "category": "semantic_structure",
                "issue": "Semantic structure requires review",
                "scope": "page",
                "severity": "critical",
                "confidence": "medium",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
            }
        ]
    }

    output = build_output(data)

    recommendation = output["recommendations"][0]

    assert recommendation["priority"] == "critical"


def test_unknown_category_is_supported():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-unknown",
                "category": "custom_issue",
                "issue": "Custom issue requires review",
                "scope": "site",
                "confidence": "medium",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
            }
        ]
    }

    output = build_output(data)

    recommendation = output["recommendations"][0]

    assert recommendation["category"] == "custom_issue"
    assert recommendation["title"]
    assert recommendation["action"]
    assert recommendation["verification"]


def test_affected_pages_are_deduplicated_and_sorted():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-pages",
                "category": "entity_identity",
                "issue": "Identity issue",
                "scope": "site",
                "confidence": "high",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [
                    "https://example.com/z",
                    "https://example.com/a",
                    "https://example.com/z",
                ],
                "evidence": [],
            }
        ]
    }

    output = build_output(data)

    pages = output["recommendations"][0]["affected_pages"]

    assert pages == [
        "https://example.com/a",
        "https://example.com/z",
    ]


def test_limitations_are_preserved():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-limited",
                "category": "render_observability",
                "issue": "Render issue",
                "scope": "page",
                "confidence": "medium",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
                "limitations": [
                    "Rendered state could not be fully verified"
                ],
            }
        ],
        "limitations": [
            "Browser rendering was unavailable"
        ],
    }

    output = build_output(data)

    recommendation = output["recommendations"][0]

    assert recommendation["limitations"] == [
        "Rendered state could not be fully verified"
    ]

    assert output["limitations"] == [
        "Browser rendering was unavailable"
    ]


def test_deterministic_order():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-z",
                "category": "navigation_pathway",
                "issue": "Navigation issue",
                "scope": "page",
                "confidence": "medium",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
            },
            {
                "candidate_id": "candidate-a",
                "category": "machine_structure",
                "issue": "Machine issue",
                "scope": "page",
                "confidence": "high",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
            },
        ]
    }

    output_one = build_output(data)
    output_two = build_output(data)

    assert json.dumps(
        output_one,
        sort_keys=True,
    ) == json.dumps(
        output_two,
        sort_keys=True,
    )

    assert (
        output_one["recommendations"][0]["priority"]
        == "high"
    )


def test_summary_counts():
    data = {
        "findings": [
            {
                "candidate_id": "candidate-high",
                "category": "machine_structure",
                "issue": "Machine issue",
                "scope": "page",
                "confidence": "high",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
            },
            {
                "candidate_id": "candidate-medium",
                "category": "engagement_pathway",
                "issue": "Engagement issue",
                "scope": "page",
                "confidence": "medium",
                "evidence_sufficiency": "sufficient",
                "affected_pages": [],
                "evidence": [],
            },
            {
                "candidate_id": "candidate-low",
                "category": "freshness_signal",
                "issue": "Freshness issue",
                "scope": "page",
                "confidence": "low",
                "evidence_sufficiency": "insufficient",
                "affected_pages": [],
                "evidence": [],
            },
        ]
    }

    output = build_output(data)

    summary = output["summary"]

    assert summary["recommendations_generated"] == 3
    assert summary["high_priority"] == 1
    assert summary["medium_priority"] == 1
    assert summary["low_priority"] == 1
    assert summary["verification_required"] == 1


if __name__ == "__main__":
    tests = [
        (
            "test_empty_input",
            test_empty_input,
        ),
        (
            "test_high_confidence_machine_structure",
            test_high_confidence_machine_structure,
        ),
        (
            "test_medium_confidence_engagement",
            test_medium_confidence_engagement,
        ),
        (
            "test_low_confidence",
            test_low_confidence,
        ),
        (
            "test_insufficient_evidence_requires_verification",
            test_insufficient_evidence_requires_verification,
        ),
        (
            "test_explicit_severity_is_preserved",
            test_explicit_severity_is_preserved,
        ),
        (
            "test_unknown_category_is_supported",
            test_unknown_category_is_supported,
        ),
        (
            "test_affected_pages_are_deduplicated_and_sorted",
            test_affected_pages_are_deduplicated_and_sorted,
        ),
        (
            "test_limitations_are_preserved",
            test_limitations_are_preserved,
        ),
        (
            "test_deterministic_order",
            test_deterministic_order,
        ),
        (
            "test_summary_counts",
            test_summary_counts,
        ),
    ]

    for name, test in tests:
        run_test(name, test)

    print(f"\n{len(tests)}/{len(tests)} tests passed.")