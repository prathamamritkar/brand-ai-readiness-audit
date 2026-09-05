#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("analyze_crawl_render.py")


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


def test_content_observability():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/about",
                "page_type": "about",
                "fetch": {"ok": True},
                "title": "About Example",
                "visible_text": "Example company information",
                "visible_text_chars": 27,
                "headings": ["About"],
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["content_observability"][0]

    assert item["status"] == "present"
    assert item["visible_text_chars"] == 27
    assert item["heading_count"] == 1


def test_empty_static_evidence_is_not_claimed_as_rendering_failure():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/app",
                "page_type": "other",
                "fetch": {"ok": True},
                "visible_text": "",
                "visible_text_chars": 0,
                "headings": [],
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["content_observability"][0]

    assert item["status"] == "unable_to_determine"


def test_failed_fetch_is_unable_to_determine():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/contact",
                "page_type": "contact",
                "fetch": {
                    "ok": False,
                    "error": "blocked",
                },
                "visible_text": "",
                "visible_text_chars": 0,
                "headings": [],
            }
        ]
    }

    result = run_analyzer(bundle)

    assert (
        result["content_observability"][0]["status"]
        == "unable_to_determine"
    )


def test_semantic_structure():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Example",
                "headings": ["Welcome", "Products"],
                "meta_description": "Example company",
                "canonical": "https://example.com/",
                "language": "en",
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["semantic_structure"][0]

    assert item["title"]["status"] == "present"
    assert item["headings"]["status"] == "present"
    assert item["headings"]["count"] == 2
    assert item["meta_description"]["status"] == "present"
    assert item["canonical"]["status"] == "present"
    assert item["language"]["status"] == "present"


def test_missing_semantic_signals_are_absent():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "",
                "headings": [],
                "meta_description": "",
                "canonical": "",
                "language": "",
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["semantic_structure"][0]

    assert item["title"]["status"] == "absent"
    assert item["headings"]["status"] == "absent"
    assert item["meta_description"]["status"] == "absent"
    assert item["canonical"]["status"] == "absent"
    assert item["language"]["status"] == "absent"


def test_machine_relationships():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/",
                "canonical": "https://example.com/",
                "links": [
                    "https://example.com/about",
                    "https://example.com/products",
                    "https://external.example.org/resource",
                ],
                "jsonld": [
                    {
                        "@context": "https://schema.org",
                        "@type": "Organization",
                    }
                ],
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["machine_relationships"][0]

    assert item["internal_link_count"] == 2
    assert item["external_link_count"] == 1
    assert item["canonical"]["status"] == "present"
    assert item["structured_relationships"]["status"] == "present"
    assert item["structured_relationships"]["types"] == ["Organization"]


def test_jsonld_graph_types():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/product",
                "jsonld": [
                    {
                        "@context": "https://schema.org",
                        "@graph": [
                            {
                                "@type": "Product",
                            },
                            {
                                "@type": ["Organization", "WebSite"],
                            },
                        ],
                    }
                ],
            }
        ]
    }

    result = run_analyzer(bundle)

    item = result["structured_rendering"][0]

    assert item["status"] == "present"
    assert item["jsonld_block_count"] == 1
    assert item["observable_types"] == [
        "Organization",
        "Product",
        "WebSite",
    ]


def test_summary():
    bundle = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "fetch": {"ok": True},
                "title": "Example",
                "headings": ["Welcome"],
                "meta_description": "Example",
                "visible_text_chars": 100,
                "links": [
                    "https://example.com/about",
                ],
                "jsonld": [],
            },
            {
                "url": "https://example.com/about",
                "page_type": "about",
                "fetch": {"ok": True},
                "title": "About",
                "headings": [],
                "meta_description": "",
                "visible_text_chars": 50,
                "links": [],
                "jsonld": [],
            },
        ]
    }

    result = run_analyzer(bundle)

    summary = result["summary"]

    assert summary["pages_analyzed"] == 2
    assert summary["pages_with_observable_content"] == 2
    assert summary["pages_with_titles"] == 2
    assert summary["pages_with_headings"] == 1
    assert summary["pages_with_meta_descriptions"] == 1
    assert summary["pages_with_structured_data"] == 0
    assert summary["pages_with_internal_links"] == 1
    assert summary["page_type_distribution"] == {
        "about": 1,
        "homepage": 1,
    }


def test_empty_bundle():
    result = run_analyzer({"pages": []})

    assert result["skill"] == "crawl-render-audit"
    assert result["schema_version"] == "crawl-render-audit/v1"
    assert result["summary"]["pages_analyzed"] == 0
    assert result["content_observability"] == []
    assert result["semantic_structure"] == []
    assert result["machine_relationships"] == []
    assert result["structured_rendering"] == []
    assert len(result["limitations"]) > 0


if __name__ == "__main__":
    tests = [
        test_content_observability,
        test_empty_static_evidence_is_not_claimed_as_rendering_failure,
        test_failed_fetch_is_unable_to_determine,
        test_semantic_structure,
        test_missing_semantic_signals_are_absent,
        test_machine_relationships,
        test_jsonld_graph_types,
        test_summary,
        test_empty_bundle,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\n{len(tests)}/{len(tests)} tests passed")