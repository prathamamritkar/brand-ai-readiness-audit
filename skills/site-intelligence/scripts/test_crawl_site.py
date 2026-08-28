import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from crawl_site import normalize_url, clean_link, PageParser


class CrawlSiteTests(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com/")
        self.assertEqual(normalize_url("https://Example.COM/a#x"), "https://example.com/a")

    def test_clean_link(self):
        self.assertEqual(clean_link("https://example.com/a", "/b"), "https://example.com/b")
        self.assertIsNone(clean_link("https://example.com/a", "mailto:test@example.com"))

    def test_page_parser(self):
        html = """
        <html><head>
          <title>Example Product</title>
          <meta name="description" content="A product.">
          <link rel="canonical" href="/products/x">
          <script type="application/ld+json">{"@type":"Product"}</script>
        </head><body>
          <h1>Product X</h1>
          <p>Useful product information.</p>
          <a href="/about">About</a>
          <script>hidden implementation detail</script>
        </body></html>
        """
        p = PageParser("https://example.com/products/x")
        p.feed(html)
        result = p.evidence()

        self.assertEqual(result["title"], "Example Product")
        self.assertEqual(result["canonical"], "https://example.com/products/x")
        self.assertEqual(result["headings"], [{"level": 1, "text": "Product X"}])
        self.assertEqual(result["links"], ["https://example.com/about"])
        self.assertEqual(len(result["jsonld_blocks"]), 1)
        self.assertIn("Useful product information.", " ".join(p.text_parts))
        self.assertNotIn("hidden implementation detail", " ".join(p.text_parts))


if __name__ == "__main__":
    unittest.main()
