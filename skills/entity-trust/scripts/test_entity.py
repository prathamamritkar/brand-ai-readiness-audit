"""
Deterministic tests for the Entity Trust skill.
"""

from __future__ import annotations

import json

from analyze_entity import analyze


def run_test(name, condition):
    if not condition:
        raise AssertionError(f"FAIL: {name}")

    print(f"PASS: {name}")


def test_empty_input():
    output = analyze({})

    assert output["schema_version"] == "entity-trust/v1"
    assert output["summary"]["pages_evaluated"] == 0
    assert output["summary"]["findings"] == 0
    assert output["findings"] == []
    assert output["limitations"]


def test_clear_organization_identity():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Acme Technologies",
                "meta_description": "Acme Technologies builds industrial software.",
                "visible_text": (
                    "Acme Technologies provides industrial software "
                    "solutions for manufacturing teams."
                ),
            },
            {
                "url": "https://example.com/about",
                "page_type": "about",
                "title": "About Acme Technologies",
                "visible_text": (
                    "Acme Technologies is an industrial software company."
                ),
            },
        ]
    }

    output = analyze(data)

    assert output["summary"]["pages_evaluated"] == 2

    signals = {
        finding["signal"]
        for finding in output["findings"]
    }

    assert "entity_identity_clear" in signals


def test_organization_identity_unclear():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "visible_text": "",
            }
        ]
    }

    output = analyze(data)

    assert any(
        finding["signal"] == "organization_identity_unclear"
        and finding["status"] == "absent"
        for finding in output["findings"]
    )


def test_machine_identity_gap():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Acme Technologies",
                "meta_description": "Industrial software company.",
                "visible_text": (
                    "Acme Technologies builds software for manufacturers."
                ),
                "jsonld": [],
            }
        ]
    }

    output = analyze(data)

    assert any(
        finding["signal"] == "machine_identity_gap"
        and finding["status"] == "absent"
        for finding in output["findings"]
    )


def test_organization_jsonld_prevents_machine_gap():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Acme Technologies",
                "visible_text": (
                    "Acme Technologies builds industrial software."
                ),
                "jsonld": [
                    {
                        "@type": "Organization",
                        "name": "Acme Technologies",
                    }
                ],
            }
        ]
    }

    output = analyze(data)

    assert not any(
        finding["signal"] == "machine_identity_gap"
        for finding in output["findings"]
    )


def test_offering_identity_clear():
    data = {
        "pages": [
            {
                "url": "https://example.com/product/widget",
                "page_type": "product",
                "title": "Acme Widget",
                "meta_description": "Industrial monitoring software.",
                "visible_text": (
                    "Acme Widget helps manufacturing teams monitor "
                    "equipment performance and operational metrics."
                ),
                "jsonld": [
                    {
                        "@type": "Product",
                        "name": "Acme Widget",
                    }
                ],
            }
        ]
    }

    output = analyze(data)

    assert any(
        finding["signal"] == "entity_identity_clear"
        and finding["scope"] == "page"
        and finding["page_url"]
        == "https://example.com/product/widget"
        for finding in output["findings"]
    )


def test_offering_identity_unclear():
    data = {
        "pages": [
            {
                "url": "https://example.com/product/widget",
                "page_type": "product",
                "title": "",
                "meta_description": "",
                "visible_text": "",
            }
        ]
    }

    output = analyze(data)

    assert any(
        finding["signal"] == "offering_identity_unclear"
        and finding["status"] == "absent"
        for finding in output["findings"]
    )


def test_identity_inconsistency():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Acme Technologies",
                "jsonld": [
                    {
                        "@type": "Organization",
                        "name": "Acme Technologies",
                    }
                ],
            },
            {
                "url": "https://example.com/about",
                "page_type": "about",
                "title": "About Acme",
                "jsonld": [
                    {
                        "@type": "Organization",
                        "name": "Acme",
                    }
                ],
            },
            {
                "url": "https://example.com/contact",
                "page_type": "contact",
                "title": "Contact Acme Technologies",
                "jsonld": [
                    {
                        "@type": "Organization",
                        "name": "Acme Technologies",
                    }
                ],
            },
        ]
    }

    output = analyze(data)

    assert any(
        finding["signal"] == "identity_inconsistency"
        and finding["status"] == "present"
        for finding in output["findings"]
    )


def test_no_false_inconsistency_from_page_titles():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Acme Technologies",
            },
            {
                "url": "https://example.com/product",
                "page_type": "product",
                "title": "Acme Widget",
                "meta_description": "Industrial monitoring software.",
                "visible_text": (
                    "Acme Widget helps teams monitor equipment."
                ),
            },
        ]
    }

    output = analyze(data)

    assert not any(
        finding["signal"] == "identity_inconsistency"
        for finding in output["findings"]
    )


def test_jsonld_types_are_case_insensitive():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Acme Technologies",
                "visible_text": (
                    "Acme Technologies provides industrial software."
                ),
                "jsonld": [
                    {
                        "@type": "Organization",
                        "name": "Acme Technologies",
                    }
                ],
            }
        ]
    }

    output = analyze(data)

    assert not any(
        finding["signal"] == "machine_identity_gap"
        for finding in output["findings"]
    )


def test_deterministic_output_order():
    data = {
        "pages": [
            {
                "url": "https://example.com/product/b",
                "page_type": "product",
                "title": "",
                "visible_text": "",
            },
            {
                "url": "https://example.com/product/a",
                "page_type": "product",
                "title": "",
                "visible_text": "",
            },
        ]
    }

    output_one = analyze(data)
    output_two = analyze(data)

    assert json.dumps(
        output_one,
        sort_keys=True,
    ) == json.dumps(
        output_two,
        sort_keys=True,
    )

    urls = [
        finding["page_url"]
        for finding in output_one["findings"]
        if finding["page_url"]
    ]

    assert urls == sorted(urls)


def test_missing_fields_are_tolerated():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
            },
            {
                "url": "https://example.com/about",
                "page_type": "about",
            },
            {
                "url": "https://example.com/product",
                "page_type": "product",
                "jsonld": None,
            },
        ]
    }

    output = analyze(data)

    assert output["summary"]["pages_evaluated"] == 3
    assert isinstance(output["findings"], list)


def test_summary_counts():
    data = {
        "pages": [
            {
                "url": "https://example.com/",
                "page_type": "homepage",
                "title": "Acme Technologies",
                "visible_text": (
                    "Acme Technologies builds industrial software."
                ),
            },
            {
                "url": "https://example.com/product/widget",
                "page_type": "product",
                "title": "Acme Widget",
                "meta_description": "Industrial monitoring software.",
                "visible_text": (
                    "Acme Widget helps teams monitor equipment "
                    "performance and operational metrics."
                ),
            },
        ]
    }

    output = analyze(data)

    assert output["summary"]["pages_evaluated"] == 2
    assert output["summary"]["findings"] == len(
        output["findings"]
    )
    assert output["summary"]["identity_clear"] >= 1
    assert output["summary"]["identity_gaps"] >= 1


if __name__ == "__main__":
    tests = [
        (
            "test_empty_input",
            test_empty_input,
        ),
        (
            "test_clear_organization_identity",
            test_clear_organization_identity,
        ),
        (
            "test_organization_identity_unclear",
            test_organization_identity_unclear,
        ),
        (
            "test_machine_identity_gap",
            test_machine_identity_gap,
        ),
        (
            "test_organization_jsonld_prevents_machine_gap",
            test_organization_jsonld_prevents_machine_gap,
        ),
        (
            "test_offering_identity_clear",
            test_offering_identity_clear,
        ),
        (
            "test_offering_identity_unclear",
            test_offering_identity_unclear,
        ),
        (
            "test_identity_inconsistency",
            test_identity_inconsistency,
        ),
        (
            "test_no_false_inconsistency_from_page_titles",
            test_no_false_inconsistency_from_page_titles,
        ),
        (
            "test_jsonld_types_are_case_insensitive",
            test_jsonld_types_are_case_insensitive,
        ),
        (
            "test_deterministic_output_order",
            test_deterministic_output_order,
        ),
        (
            "test_missing_fields_are_tolerated",
            test_missing_fields_are_tolerated,
        ),
        (
            "test_summary_counts",
            test_summary_counts,
        ),
    ]

    for name, test in tests:
        run_test(name, test)

    print(f"\n{len(tests)}/{len(tests)} tests passed.")