"""
Shared DOM Fetcher for the Brand AI-Readiness Audit Marketplace.

Fetches the target URL exactly ONCE and returns a PageContext dict
that all sub-skills consume. This eliminates duplicate network calls
and ensures every skill analyzes the exact same DOM snapshot.
"""

import urllib.robotparser
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def fetch_page(url, timeout=30):
    """
    Fetch a URL and return a PageContext dict containing all data
    needed by every sub-skill in the marketplace.

    Returns:
        dict with keys:
            url (str): The original target URL.
            base_url (str): Scheme + netloc (e.g., https://example.com).
            raw_html (str): Full response body text.
            soup (BeautifulSoup): Parsed DOM (un-mutated original).
            robots_parser (RobotFileParser): Parsed robots.txt rules.
            robots_txt_raw (str): Raw robots.txt content for sitemap extraction.
            status_code (int): HTTP response status code.
            response_headers (dict): HTTP response headers.
            fetch_error (str|None): None if successful, error message otherwise.
    """
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    context = {
        "url": url,
        "base_url": base_url,
        "parsed_url": parsed_url,
        "raw_html": "",
        "soup": None,
        "robots_parser": None,
        "robots_txt_raw": "",
        "status_code": None,
        "response_headers": {},
        "fetch_error": None,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BrandAuditBot/2.0; +https://agentskills.io)"
    }

    # --- Fetch robots.txt ---
    rp = urllib.robotparser.RobotFileParser()
    robots_url = f"{base_url}/robots.txt"
    rp.set_url(robots_url)
    try:
        rp.read()
        context["robots_parser"] = rp
        # Also fetch raw text for sitemap directive extraction
        try:
            robots_resp = requests.get(robots_url, headers=headers, timeout=10)
            if robots_resp.status_code == 200:
                context["robots_txt_raw"] = robots_resp.text
        except Exception:
            pass  # Raw text is optional; parser already loaded
    except Exception:
        # No robots.txt or unreachable — assume fully accessible
        context["robots_parser"] = rp

    # --- Fetch the target URL ---
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        context["raw_html"] = response.text
        context["status_code"] = response.status_code
        context["response_headers"] = dict(response.headers)
        context["soup"] = BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.Timeout:
        context["fetch_error"] = f"HTTP request timed out after {timeout}s for {url}"
    except requests.exceptions.ConnectionError:
        context["fetch_error"] = f"Connection failed for {url} — host may be unreachable"
    except Exception as e:
        context["fetch_error"] = f"Failed to fetch {url}: {str(e)}"

    return context

