import unittest

from analyze_engagement import (
    analyze,
    classify_anchor,
    normalize_url,
)


class EngagementAuditTests(unittest.TestCase):

    def test_normalize_url(self):
        url = "HTTPS://Example.COM/pricing#plans"

        self.assertEqual(
            normalize_url(url),
            "https://example.com/pricing"
        )

    def test_action_anchor_detection(self):
        result = classify_anchor("View Pricing")

        self.assertTrue(
            result["action"]
        )

        self.assertIn(
            "pricing",
            result["contexts"]
        )

    def test_generic_anchor_detection(self):
        result = classify_anchor("Click Here")

        self.assertFalse(
            result["action"]
        )

        self.assertTrue(
            result["generic"]
        )

    def test_context_anchor_detection(self):
        result = classify_anchor(
            "Read our case studies"
        )

        self.assertIn(
            "case_study",
            result["contexts"]
        )

    def test_link_and_navigation_observations(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/",
                    "page_type": "homepage",
                    "links": [
                        {
                            "url": "https://example.com/pricing",
                            "anchor_text": "View Pricing",
                        },
                        {
                            "url": "https://example.com/about",
                            "anchor_text": "About Us",
                        },
                        {
                            "url": "https://external.example.com/",
                            "anchor_text": "Partner",
                        },
                    ],
                },
                {
                    "url": "https://example.com/pricing",
                    "page_type": "pricing",
                    "links": [
                        {
                            "url": "https://example.com/contact",
                            "anchor_text": "Contact Sales",
                        }
                    ],
                },
            ]
        }

        result = analyze(bundle)

        self.assertEqual(
            result["summary"]["pages_analyzed"],
            2
        )

        self.assertEqual(
            result["summary"]["links_analyzed"],
            4
        )

        self.assertEqual(
            result["summary"]["internal_links"],
            3
        )

        self.assertEqual(
            result["summary"]["external_links"],
            1
        )

        self.assertEqual(
            result["summary"]["action_links"],
            2
        )

        self.assertGreaterEqual(
            result["summary"]["navigation_pathways"],
            3
        )

    def test_page_engagement_signals(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/product",
                    "page_type": "product",
                    "links": [
                        {
                            "url": "https://example.com/pricing",
                            "anchor_text": "View Pricing",
                        },
                        {
                            "url": "https://example.com/docs",
                            "anchor_text": "Documentation",
                        },
                    ],
                }
            ]
        }

        result = analyze(bundle)

        page_engagement = [
            item
            for item in result["observations"]
            if item.get("type")
            == "page_engagement"
        ]

        self.assertEqual(
            len(page_engagement),
            1
        )

        self.assertEqual(
            page_engagement[0]["next_action_status"],
            "present"
        )

        self.assertEqual(
            page_engagement[0]["signals"]["action_links"],
            1
        )

        self.assertEqual(
            page_engagement[0]["signals"]["documentation_links"],
            1
        )

    def test_contextual_link_observation(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/article",
                    "page_type": "blog",
                    "links": [
                        {
                            "url": "https://example.com/case-study",
                            "anchor_text": "Read our case study",
                        }
                    ],
                }
            ]
        }

        result = analyze(bundle)

        contextual = [
            item
            for item in result["observations"]
            if item.get("type")
            == "contextual_link"
        ]

        self.assertEqual(
            len(contextual),
            1
        )

        self.assertIn(
            "case_study",
            contextual[0]["contexts"]
        )

    def test_generic_and_empty_links(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/",
                    "page_type": "homepage",
                    "links": [
                        {
                            "url": "https://example.com/about",
                            "anchor_text": "Click Here",
                        },
                        {
                            "url": "https://example.com/contact",
                            "anchor_text": "",
                        },
                    ],
                }
            ]
        }

        result = analyze(bundle)

        self.assertEqual(
            result["summary"]["generic_anchor_links"],
            2
        )

    def test_current_string_link_format(self):
        bundle = {
            "pages": [
                {
                    "url": "https://example.com/",
                    "page_type": "homepage",
                    "links": [
                        "https://example.com/about"
                    ],
                }
            ]
        }

        result = analyze(bundle)

        self.assertEqual(
            result["summary"]["links_analyzed"],
            1
        )

        self.assertEqual(
            result["summary"]["internal_links"],
            1
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
            result["summary"]["links_analyzed"],
            0
        )

        self.assertEqual(
            result["summary"]["action_links"],
            0
        )

        self.assertEqual(
            result["coverage"]["action_page_coverage"],
            0
        )


if __name__ == "__main__":
    unittest.main()