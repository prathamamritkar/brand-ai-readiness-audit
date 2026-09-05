---
name: discoverability-audit
description: Audits a website's underlying DOM for AI discoverability signals, mapping standard SEO hygiene (JSON-LD, robots.txt, semantic HTML) to identify root causes of poor AI visibility.
license: Apache-2.0
---

# Discoverability Audit

## When to use
Use this skill when determining why a brand is missing, hallucinated, or misrepresented by AI assistants. It extracts raw structural data to find underlying reasons for poor visibility without relying on hardcoded scraping paths.

## Inputs
* `url`: The target website URL (e.g., `https://example.com`).

## Procedure
1. Receive the target URL.
2. Fetch the raw DOM and check `robots.txt` permissions.
3. Search for universal mapping standards like Schema.org JSON-LD structured data.
4. Compare raw HTML text volume against JavaScript-dependent rendering to identify trapped facts.
5. Output findings prioritized by their impact on machine readability.

## Output
A JSON array of findings. Each finding includes an `id`, `title`, `severity` (critical, high, medium), `evidence` extracted directly from the DOM, and a `suggested_action` for remediation.