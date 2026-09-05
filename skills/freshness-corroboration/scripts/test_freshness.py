#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("analyze_freshness.py")


def run_analyzer(bundle):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "evidence.json"

        with open(input_path, "w", encoding="utf-8") as handle:
            json.dump(bundle, handle)

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(input_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr

        return json.loads(completed.stdout)


def test_structured_publication_date():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/article",
                "page_type": "blog",
                "jsonld": [
                    {
                        "@context": "https://schema.org",
                        "@type": "Article",
                        "datePublished": "2026-08-20",
                    }
                ],
            }
        ]
    }

    result = run_analyzer(bundle)

    assert result["summary"]["pages_with_publication_signals"] == 1

    signal = result["structured_date_signals"][0]

    assert signal["property"] == "datePublished"
    assert signal["normalized_date"] == "2026-08-20"


def test_structured_modified_date_in_graph():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/article",
                "page_type": "article",
                "jsonld": [
                    {
                        "@context": "https://schema.org",
                        "@graph": [
                            {
                                "@type": "Article",
                                "dateModified": "2026-08-21T10:30:00Z",
                            }
                        ],
                    }
                ],
            }
        ]
    }

    result = run_analyzer(bundle)

    signal = result["structured_date_signals"][0]

    assert signal["property"] == "dateModified"
    assert signal["normalized_date"] == "2026-08-21"


def test_visible_date():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/blog",
                "page_type": "blog",
                "visible_text": (
                    "Published August 20, 2026. "
                    "This is the article content."
                ),
                "headings": [],
            }
        ]
    }

    result = run_analyzer(bundle)

    assert result["summary"]["pages_with_visible_date_signals"] == 1

    signal = result["visible_date_signals"][0]

    assert signal["signal_type"] == "published"
    assert signal["normalized_date"] == "2026-08-20"


def test_corroborated_date():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/article",
                "page_type": "article",
                "visible_text": "Published August 20, 2026.",
                "jsonld": [
                    {
                        "@context": "https://schema.org",
                        "@type": "Article",
                        "datePublished": "2026-08-20",
                    }
                ],
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["corroboration"][0][0]

    assert item["signal_type"] == "published"
    assert item["relationship"] == "corroborated"


def test_conflicting_date():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/article",
                "page_type": "article",
                "visible_text": "Published August 20, 2026.",
                "jsonld": [
                    {
                        "@context": "https://schema.org",
                        "@type": "Article",
                        "datePublished": "2025-11-03",
                    }
                ],
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["corroboration"][0][0]

    assert item["signal_type"] == "published"
    assert item["relationship"] == "conflicting"


def test_single_source():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/article",
                "page_type": "article",
                "jsonld": [
                    {
                        "@context": "https://schema.org",
                        "@type": "Article",
                        "dateModified": "2026-08-21",
                    }
                ],
            }
        ]
    }

    result = run_analyzer(bundle)

    updated = [
        item
        for item in result["corroboration"][0]
        if item["signal_type"] == "updated"
    ][0]

    assert updated["relationship"] == "single_source"


def test_unrelated_year_is_not_freshness_signal():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "visible_text": (
                    "Serving customers since 1998. "
                    "Our company history."
                ),
            }
        ]
    }

    result = run_analyzer(bundle)

    assert result["visible_date_signals"] == []
    assert (
        result["summary"]["pages_with_visible_date_signals"]
        == 0
    )


def test_empty_bundle():
    result = run_analyzer({"pages": []})

    assert result["skill"] == "freshness-corroboration"
    assert result["schema_version"] == "freshness-corroboration/v1"
    assert result["summary"]["pages_analyzed"] == 0
    assert result["publication_signals"] == []
    assert result["modification_signals"] == []
    assert result["visible_date_signals"] == []
    assert result["structured_date_signals"] == []
    assert len(result["limitations"]) > 0


if __name__ == "__main__":
    tests = [
        test_structured_publication_date,
        test_structured_modified_date_in_graph,
        test_visible_date,
        test_corroborated_date,
        test_conflicting_date,
        test_single_source,
        test_unrelated_year_is_not_freshness_signal,
        test_empty_bundle,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\n{len(tests)}/{len(tests)} tests passed")