---
name: security-trust-audit
description: >
  Evaluates whether a website presents the trust and security signals
  that AI systems use to determine source credibility. Checks HTTPS
  enforcement, security headers, privacy indicators, and trust markers
  that influence whether an AI assistant will cite the brand as authoritative.
license: Apache-2.0
---

# Security & Trust Audit

## When to use
Use this skill to evaluate whether a website's security posture and trust signals meet the threshold for AI citation credibility. AI systems deprioritize sources that lack basic security hygiene or trust indicators.

## Inputs
* `soup` (BeautifulSoup): Parsed DOM of the target page.
* `response_headers` (dict): HTTP response headers from the page fetch.
* `url` (str): The target URL being audited.
* `base_url` (str): Scheme + netloc (e.g., `https://example.com`).

## Heuristics (7)

| ID | Title | Severity | What It Checks |
|----|-------|----------|----------------|
| ST-001 | HTTPS Not Enforced | critical | URL scheme is HTTP, not HTTPS |
| ST-002 | Missing HSTS Header | high | No Strict-Transport-Security header |
| ST-003 | Missing Content-Security-Policy | medium | No CSP header to prevent XSS |
| ST-004 | Missing X-Content-Type-Options | medium | No nosniff directive |
| ST-005 | Missing X-Frame-Options | medium | No clickjacking protection |
| ST-006 | No Privacy/Terms Page Linked | medium | No visible privacy policy or terms links |
| ST-007 | [Proactive] Missing Referrer-Policy | medium | No Referrer-Policy header set |

## Output
A list of finding dicts matching the standard marketplace finding schema.
