---
name: crawl-render-audit
description: Audits crawler accessibility and content machine-readability. Separates indexing gaps (page unreachable or unreadable by a crawler) from citation gaps (page reachable but lacking signals that cause AI assistants to quote it).
license: Apache-2.0
metadata:
  entrypoint: false
  version: 3.0.0
allowed-tools:
  - python-runtime
---

# Crawl & Render Audit

## When to use
Diagnose why a page is absent from AI assistant answers — either because a crawler cannot reach it (indexing gap) or because it is reached but not quoted (citation gap).

## Inputs
* `url` (string, required): Page URL.
* `page_data` (dict): `{status_code, headers, html, word_count, script_bytes}` from the orchestrator crawl. All fields may be absent if the page errored — handle gracefully.

## Procedure

If `page_data` is absent or `status_code` is not 2xx, emit a single `high` `indexing` finding and return. Do not attempt further checks on unreachable pages.

### Indexing Checks (`gap_type: "indexing"`)

1. **Meta robots directive**: Parse `<meta name="robots" content="...">` from HTML (case-insensitive). If `noindex` or `none` is present → `critical`. Evidence: report the full content attribute value.

2. **X-Robots-Tag response header**: Check response headers for `X-Robots-Tag`. If it contains `noindex` → `critical`. Evidence: report the header value as found. Skip if header absent.

3. **CSR rendering barrier**: If `word_count < 150` and `script_bytes > 40000`, infer likely client-side rendering. Confirm by scanning raw HTML for framework hydration markers: `data-reactroot`, `ng-version`, `__nuxt`, `__NEXT_DATA__`, `data-server-rendered`, `__svelte`. If any marker found alongside low visible text → `high`. Evidence: state `word_count`, `script_bytes`, and which marker was detected. Suggested action scope: `site` (affects all pages rendered by the same framework).

4. **Canonical tag**: On content pages (`word_count > 100`): check for `<link rel="canonical" href="...">`. If absent → `medium`. If present but `href` differs from the current page URL (after normalization), flag separately as `medium` canonical mismatch. Evidence: report the canonical href found.

### Citation Checks (`gap_type: "citation"`)

5. **Structured data — JSON-LD**: Extract all `<script type="application/ld+json">` blocks. For each block, attempt `json.loads()`. On parse failure → `medium` (malformed JSON-LD; AI extractors will skip it). Evidence: report the parse error and first 120 characters of the block. If no JSON-LD blocks present at all → `high`. If e-commerce signals are present in visible text (price patterns via regex, phrases like "add to cart", "buy now") but no `Product` or `Offer` `@type` found in any valid block → `high`. If no `BreadcrumbList` found on a non-root page with more than one path segment → `medium`.

6. **Semantic HTML structure**: Missing `<main>` or `<article>` landmark element → `medium`. Zero `<h1>` elements → `medium`. More than one `<h1>` → `medium`. Evidence: report the actual count found.

7. **`<title>` and meta description**: `<title>` absent or empty → `high` (primary AI snippet surface). `<meta name="description">` absent or empty → `medium`. Description longer than 160 characters → `medium` (likely truncated in AI previews). Evidence: report what was found.

8. **Machine-readable AI manifest** (root URL only): `GET /llms.txt` (new HEAD request, 5 s timeout). On 404 or non-2xx → `medium`. On 2xx but response body less than 50 bytes or body does not start with `#` → `medium` (malformed). This is a citation signal. Evidence: report HTTP status and first line of body if available.

9. **Open Graph tags**: Missing `og:title` → `medium`. Missing `og:description` → `medium`. Both missing simultaneously → consolidate into one `high` finding. Evidence: list which tags were absent.

10. **Multi-region signal** (root URL only): If `<link rel="alternate" hreflang>` tags are present, check for a tag with `hreflang="x-default"`. If absent → `medium`. If present but one or more region tags point to non-2xx URLs → `medium`. Skip entirely if no hreflang tags are found (not a defect for single-region sites).

## Output
Finding records. `gap_type`: `"indexing"` or `"citation"`. `category`: `"discoverability"`.
