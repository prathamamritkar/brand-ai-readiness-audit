import unittest

from analyze_machine_readability import (
    analyze,
    extract_schema_types,
    normalize_url,
)


class MachineReadabilityTests(unittest.TestCase):

    def test_extract_schema_types(self):
        block = {
            "@type": ["Organization", "WebSite"],
            "name": "Example"
        }

        self.assertEqual(
            extract_schema_types(block),
            ["Organization", "WebSite"]
        )

    def test_normalize_url(self):
        url = "HTTPS://Example.COM/page#section"

        self.assertEqual(
            normalize_url(url),
            "https://example.com/page"
        )

    def test_jsonld_observation(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/",
                    "title": "Example",
                    "meta_description": "Example website",
                    "canonical": "https://example.com/",
                    "headings": ["Example"],
                    "page_type": "homepage",
                    "language": "en",
                    "jsonld_blocks": [
                        {
                            "@type": "Organization",
                            "@id": "https://example.com/#organization",
                            "name": "Example Corp",
                            "url": "https://example.com/"
                        }
                    ]
                }
            ]
        }

        result = analyze(bundle)

        self.assertEqual(
            result["summary"]["pages_analyzed"],
            1
        )

        self.assertEqual(
            result["summary"]["structured_data_blocks"],
            1
        )

        self.assertEqual(
            result["summary"]["entity_observations"],
            1
        )

        self.assertEqual(
            result["coverage"]["pages_with_jsonld"],
            1
        )

        self.assertEqual(
            result["coverage"]["pages_with_entities"],
            1
        )

        self.assertEqual(
            result["coverage"]["entity_type_counts"]["Organization"],
            1
        )

    def test_jsonld_graph_entities(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/",
                    "visible_text": "Example Corp",
                    "jsonld_blocks": [
                        {
                            "@context": "https://schema.org",
                            "@graph": [
                                {
                                    "@type": "Organization",
                                    "@id": "https://example.com/#org",
                                    "name": "Example Corp"
                                },
                                {
                                    "@type": "WebSite",
                                    "@id": "https://example.com/#website",
                                    "name": "Example",
                                    "url": "https://example.com/"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        result = analyze(bundle)

        entities = [
            item
            for item in result["observations"]
            if item.get("type") == "entity"
        ]

        self.assertEqual(len(entities), 2)

        self.assertEqual(
            result["coverage"]["entity_type_counts"]["Organization"],
            1
        )

        self.assertEqual(
            result["coverage"]["entity_type_counts"]["WebSite"],
            1
        )

    def test_entity_relationships(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/",
                    "jsonld_blocks": [
                        {
                            "@type": "Organization",
                            "@id": "https://example.com/#org",
                            "name": "Example Corp",
                            "url": "https://example.com/",
                            "sameAs": [
                                "https://example.com/social"
                            ],
                            "publisher": {
                                "@id": "https://example.com/#publisher"
                            }
                        }
                    ]
                }
            ]
        }

        result = analyze(bundle)

        relationships = [
            item
            for item in result["observations"]
            if item.get("type") == "entity_relationship"
        ]

        self.assertEqual(len(relationships), 1)

        self.assertIn(
            "sameAs",
            relationships[0]["relationships"]
        )

        self.assertIn(
            "publisher",
            relationships[0]["relationships"]
        )

    def test_canonical_structured_url_consistency(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/product",
                    "title": "Product",
                    "meta_description": "Product page",
                    "canonical": "https://example.com/product",
                    "headings": ["Product"],
                    "jsonld_blocks": [
                        {
                            "@type": "Product",
                            "name": "Example Product",
                            "url": "https://example.com/product"
                        }
                    ]
                }
            ]
        }

        result = analyze(bundle)

        consistency = [
            item
            for item in result["observations"]
            if item.get("type") == "consistency"
            and item.get("check")
            == "canonical_vs_structured_url"
        ]

        self.assertEqual(len(consistency), 1)

        self.assertEqual(
            consistency[0]["status"],
            "consistent"
        )

    def test_structured_name_visible_text_consistency(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/",
                    "visible_text": (
                        "Welcome to Example Corp."
                    ),
                    "jsonld_blocks": [
                        {
                            "@type": "Organization",
                            "name": "Example Corp"
                        }
                    ]
                }
            ]
        }

        result = analyze(bundle)

        consistency = [
            item
            for item in result["observations"]
            if item.get("type") == "consistency"
            and item.get("check")
            == "structured_name_vs_visible_text"
        ]

        self.assertEqual(len(consistency), 1)

        self.assertEqual(
            consistency[0]["status"],
            "supported"
        )

    def test_page_identity_observation(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/about",
                    "title": "About Example",
                    "meta_description": "About us",
                    "canonical": "https://example.com/about",
                    "headings": [
                        "About Example"
                    ],
                    "language": "en",
                    "page_type": "about",
                    "jsonld_blocks": []
                }
            ]
        }

        result = analyze(bundle)

        identity = [
            item
            for item in result["observations"]
            if item.get("type") == "page_identity"
        ]

        self.assertEqual(len(identity), 1)

        signals = identity[0]["signals"]

        self.assertTrue(
            signals["title_present"]
        )

        self.assertTrue(
            signals["meta_description_present"]
        )

        self.assertTrue(
            signals["canonical_present"]
        )

        self.assertTrue(
            signals["language_present"]
        )

        self.assertTrue(
            signals["page_type_present"]
        )

    def test_empty_bundle(self):
        result = analyze(
            {
                "pages": []
            }
        )

        self.assertEqual(
            result["summary"]["pages_analyzed"],
            0
        )

        self.assertEqual(
            result["summary"]["structured_data_blocks"],
            0
        )

        self.assertEqual(
            result["coverage"]["jsonld_page_coverage"],
            0
        )

        self.assertEqual(
            result["coverage"]["entity_page_coverage"],
            0
        )


if __name__ == "__main__":
    unittest.main()