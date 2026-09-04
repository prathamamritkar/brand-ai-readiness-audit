import unittest
from unittest.mock import patch

import crawl_site

from crawl_site import (
    classify_page_type,
    clean_link,
    normalize_url,
)


class CrawlSiteTests(unittest.TestCase):

    def test_normalize_url(self):
        url = (
            "HTTPS://Example.COM:443/about/"
            "?utm_source=test&b=2&a=1#section"
        )

        self.assertEqual(
            normalize_url(url),
            "https://example.com/about?a=1&b=2"
        )

    def test_clean_link(self):
        self.assertEqual(
            clean_link(
                "https://example.com/products/",
                "../about#team",
            ),
            "https://example.com/about"
        )

        self.assertIsNone(
            clean_link(
                "https://example.com/",
                "mailto:test@example.com",
            )
        )

        self.assertIsNone(
            clean_link(
                "https://example.com/",
                "/document.pdf",
            )
        )

    def test_page_type(self):
        self.assertEqual(
            classify_page_type(
                "https://example.com/about"
            ),
            "about"
        )

        self.assertEqual(
            classify_page_type(
                "https://example.com/pricing"
            ),
            "pricing"
        )

        self.assertEqual(
            classify_page_type(
                "https://example.com/products/widget"
            ),
            "product"
        )

        self.assertEqual(
            classify_page_type(
                "https://example.com/"
            ),
            "homepage"
        )

    @patch(
        "crawl_site.load_robots",
        return_value={
            "available": False,
            "allowed_for_user_agent": False,
            "sitemaps": [],
            "_failure": True,
            "_parser": None,
        },
    )
    def test_robots_failure_blocks_crawl(self, mock_robots):
        result = crawl_site.crawl(
            "https://example.com/",
            max_pages=5,
            max_depth=2,
            max_bytes=1_000_000,
            timeout=5,
            max_seconds=10,
        )

        self.assertEqual(
            result["crawl"]["pages_crawled"],
            0
        )

        self.assertTrue(
            result["crawl"]["blocked_by_robots_failure"]
        )

        mock_robots.assert_called_once()


if __name__ == "__main__":
    unittest.main()