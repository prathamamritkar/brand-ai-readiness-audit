"""
Security & Trust Audit — Evaluates trust signals that influence AI citation credibility.

Checks:
  ST-001: HTTPS Not Enforced (critical)
  ST-002: Missing HSTS Header (high)
  ST-003: Missing Content-Security-Policy (medium)
  ST-004: Missing X-Content-Type-Options (medium)
  ST-005: Missing X-Frame-Options (medium)
  ST-006: No Privacy/Terms Page Linked (medium)
  ST-007: [Proactive] Missing Referrer-Policy (medium)
"""

import sys
import json
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


def _get_header(headers, name):
    """Case-insensitive header lookup."""
    for k, v in headers.items():
        if k.lower() == name.lower():
            return v
    return None


def analyze_security_trust(soup, response_headers, url, base_url):
    """
    Analyze a page for security and trust signals that affect AI citation credibility.

    Args:
        soup: BeautifulSoup parsed DOM.
        response_headers: dict of HTTP response headers.
        url: The target URL string.
        base_url: Scheme + netloc (e.g., https://example.com).

    Returns:
        List of finding dicts.
    """
    if response_headers is None:
        response_headers = {}

    findings = []
    parsed_url = urlparse(url)

    # ==========================================
    # Phase A — Transport Security
    # ==========================================

    # ST-001: HTTPS Not Enforced
    if parsed_url.scheme != "https":
        findings.append({
            "id": "ST-001",
            "title": "HTTPS Not Enforced",
            "severity": "critical",
            "evidence": f"Target URL uses '{parsed_url.scheme}://' scheme instead of 'https://'. Non-secure origins are flagged by browsers and deprioritized by AI systems as untrustworthy sources.",
            "suggested_action": {
                "summary": "Migrate the site to HTTPS with a valid TLS certificate. HTTPS is a baseline trust signal for both search engines and AI citation systems.",
                "priority": "critical"
            }
        })

    # ST-002: Missing HSTS Header
    hsts = _get_header(response_headers, "Strict-Transport-Security")
    if not hsts and parsed_url.scheme == "https":
        findings.append({
            "id": "ST-002",
            "title": "Missing HSTS Header",
            "severity": "high",
            "evidence": "No 'Strict-Transport-Security' header found. Without HSTS, browsers and crawlers may still attempt HTTP connections, and the site signals weaker transport security commitment.",
            "suggested_action": {
                "summary": "Add a Strict-Transport-Security header (e.g., 'max-age=31536000; includeSubDomains') to enforce HTTPS at the browser level and signal security maturity.",
                "priority": "high"
            }
        })

    # ==========================================
    # Phase B — Security Headers
    # ==========================================

    # ST-003: Missing Content-Security-Policy
    csp = _get_header(response_headers, "Content-Security-Policy")
    csp_ro = _get_header(response_headers, "Content-Security-Policy-Report-Only")
    if not csp and not csp_ro:
        findings.append({
            "id": "ST-003",
            "title": "Missing Content-Security-Policy",
            "severity": "medium",
            "evidence": "No 'Content-Security-Policy' header found. CSP prevents cross-site scripting (XSS) attacks — its absence signals a less security-mature site, which can reduce AI citation confidence.",
            "suggested_action": {
                "summary": "Implement a Content-Security-Policy header to define allowed resource origins. Start with a report-only policy and tighten iteratively.",
                "priority": "medium"
            }
        })

    # ST-004: Missing X-Content-Type-Options
    xcto = _get_header(response_headers, "X-Content-Type-Options")
    if not xcto:
        findings.append({
            "id": "ST-004",
            "title": "Missing X-Content-Type-Options",
            "severity": "medium",
            "evidence": "No 'X-Content-Type-Options' header found. This allows MIME-type sniffing attacks. Standard security hygiene expected of credible sites.",
            "suggested_action": {
                "summary": "Add 'X-Content-Type-Options: nosniff' header to prevent MIME-type sniffing and signal security awareness.",
                "priority": "medium"
            }
        })

    # ST-005: Missing X-Frame-Options
    xfo = _get_header(response_headers, "X-Frame-Options")
    # Also check for frame-ancestors in CSP
    has_frame_ancestors = False
    if csp and "frame-ancestors" in csp.lower():
        has_frame_ancestors = True
    if csp_ro and "frame-ancestors" in csp_ro.lower():
        has_frame_ancestors = True

    if not xfo and not has_frame_ancestors:
        findings.append({
            "id": "ST-005",
            "title": "Missing Clickjacking Protection",
            "severity": "medium",
            "evidence": "No 'X-Frame-Options' header or CSP 'frame-ancestors' directive found. The page can be embedded in malicious iframes, enabling clickjacking attacks.",
            "suggested_action": {
                "summary": "Add 'X-Frame-Options: DENY' or 'SAMEORIGIN' header, or use CSP 'frame-ancestors' directive to prevent clickjacking.",
                "priority": "medium"
            }
        })

    # ==========================================
    # Phase C — Trust Indicators
    # ==========================================

    # ST-006: No Privacy/Terms Page Linked
    _TRUST_PATTERNS = re.compile(
        r'privacy|terms\s*of\s*(?:service|use)|legal|cookie\s*policy|'
        r'datenschutz|impressum|disclaimer',
        re.IGNORECASE
    )

    trust_links_found = False
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").lower()
        text = a.get_text(strip=True).lower()
        if _TRUST_PATTERNS.search(href) or _TRUST_PATTERNS.search(text):
            trust_links_found = True
            break

    if not trust_links_found:
        findings.append({
            "id": "ST-006",
            "title": "No Privacy/Terms Page Linked",
            "severity": "medium",
            "evidence": "No links to privacy policy, terms of service, or legal pages found in the DOM. Sites without visible legal pages appear less legitimate — AI systems may deprioritize them as citation sources.",
            "suggested_action": {
                "summary": "Add visible links to privacy policy and terms of service pages, typically in the footer. These are baseline trust indicators for both humans and AI systems.",
                "priority": "medium"
            }
        })

    # ST-007: [Proactive] Missing Referrer-Policy
    referrer_policy = _get_header(response_headers, "Referrer-Policy")
    # Also check meta tag
    rp_meta = soup.find("meta", attrs={"name": re.compile(r"referrer", re.I)})
    if not referrer_policy and not rp_meta:
        findings.append({
            "id": "ST-007",
            "title": "[Proactive] Missing Referrer-Policy",
            "severity": "medium",
            "evidence": "No 'Referrer-Policy' header or meta tag found. Setting a referrer policy indicates security awareness and controls information leakage to third parties.",
            "suggested_action": {
                "summary": "Add a 'Referrer-Policy: strict-origin-when-cross-origin' header to limit referrer information shared with third-party sites.",
                "priority": "medium"
            }
        })

    return findings


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_security_trust.py <url>")
        sys.exit(1)

    target_url = sys.argv[1]

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BrandAuditBot/2.0; +https://agentskills.io)"}
        response = requests.get(target_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")

        parsed = urlparse(target_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        results = analyze_security_trust(soup, dict(response.headers), target_url, base_url)
        print(json.dumps(results, indent=2))

    except Exception as e:
        print(json.dumps([{
            "id": "ST-ERROR",
            "title": "Fetch Error",
            "severity": "critical",
            "evidence": str(e),
            "suggested_action": {
                "summary": "Fix connection issue",
                "priority": "critical"
            }
        }], indent=2))
        sys.exit(1)
