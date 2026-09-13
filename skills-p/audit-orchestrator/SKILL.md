---
name: audit-orchestrator
description: Entrypoint skill. Ingests a domain URL, runs a bounded BFS crawl, dispatches per-page and site-wide checks via sub-skills, and emits a severity-ranked JSON audit report covering AI discoverability (indexing gap + citation gap) and on-site engagement.
license: Apache-2.0
metadata:
  entrypoint: true
  version: 3.0.0
allowed-tools:
  - python-runtime
---

# Audit Orchestrator

## When to use
Audit any public website to diagnose why it is invisible to AI assistants, misrepresented by them, or why visitors who arrive from AI referrals don't engage. Produces a structured report of findings and prioritized recommendations.

## Inputs
* `url` (string, required): Target domain root (e.g. `https://example.com`).
* `max_pages` (integer, optional, default: `5`, max: `10`): Internal pages to crawl.
* `output_path` (string, optional, default: `"audit_report.json"`).

## Core Distinction — Two Discoverability Failure Modes
Every discoverability finding is tagged with `gap_type`:
* `"indexing"` — a crawler cannot reach or parse the page. The brand is absent from the AI's source pool entirely.
* `"citation"` — the page is reachable and parseable, but lacks the structured, corroborated, or fresh signals that cause an AI assistant to quote it in an answer.
* `"engagement"` — the page is cited and visited, but the visitor bounces because orientation or context is poor.

Fixing an indexing gap and fixing a citation gap require fundamentally different actions. The report must not conflate them.

## Procedure

1. **Initialize**: Normalize the URL (strip trailing slash, resolve scheme). Record `audited_at` as ISO 8601 UTC. Start a total runtime budget of **300 s** for the entire audit (crawl + all checks + emit). All HTTP fetches: 10 s timeout, `User-Agent: Mozilla/5.0 (compatible; audit-bot/1.0)`, GET only, no authentication, no cookies. Respect `Crawl-delay`. Use only: `urllib`, `requests`, `bs4` (BeautifulSoup), `xml.etree.ElementTree`, `json`, `re`, `hashlib`.

2. **robots.txt** (`gap_type: "indexing"`):
   - Fetch `/robots.txt`. On connection error or non-2xx, record `medium` finding: robots.txt absent or inaccessible — crawl posture unknown.
   - Parse with `urllib.robotparser.RobotFileParser`. Check `can_fetch()` for the root path for each known AI crawler token: `GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Bytespider`, `CCBot`, `anthropic-ai`, `cohere-ai`. Any blocked → `critical`. Evidence: list which tokens are blocked.
   - Extract `Crawl-delay` directive for use as inter-request sleep (floor: 1 s).

3. **Bounded BFS Crawl**:
   - Start from root. Follow only same-origin `<a href>` links. Normalize URLs (strip fragments, sort query params). Respect `robots.txt` per-path via `can_fetch()`. Respect `Crawl-delay`.
   - Collect per page: `{url, status_code, headers, html, word_count, script_bytes}`. `word_count`: stripped text token count. `script_bytes`: sum of `src`-less `<script>` block byte lengths.
   - On HTTP error or connection failure for any URL: record `{url, error}` in `crawl_meta.errors`; skip that URL; do not abort the run.
   - Stop when `max_pages` pages successfully fetched or queue exhausted.

4. **Dispatch Per-Page Checks**: For each successfully crawled page, invoke `crawl-render-audit`, `freshness-corroboration`, and `engagement-audit` sub-skills with `{url, page_data}`. Collect returned finding records.

5. **Site-Wide Aggregation** (run once, not per page):
   - **Sitemap**: Fetch `/sitemap.xml`. On network error or 404: emit `medium` finding (`gap_type: "citation"`, `scope: "site"`). On non-XML or XML parse failure: emit `medium` finding with parse error as evidence. On success: handle both `<sitemapindex>` (fetch and parse sub-sitemaps, one level only, skip any that fail) and `<urlset>`. Count entries with and without `<lastmod>`. If more than 50 % lack `<lastmod>`, flag `medium`. If sitemap exists but contains no URLs, flag `medium`.
   - **Cross-category semantic bleed**: Delegate to `engagement-audit` with aggregated schema data from all pages.
   - **Proactive suggestions**: Even where no explicit defect was found, evaluate: Is `SpeakableSpecification` present on any page? Is an `/llms.txt` present? Does any `Organization` JSON-LD have `sameAs`? Emit `medium` proactive recommendations for absent signals with `evidence: "not detected across crawled pages; recommended for AI citation strength"` and `scope: "site"` or `scope: "brand"`.

6. **Correlate & Emit**: Deduplicate findings by `(url, check_id)`. Sort by severity (`critical → high → medium`). Write JSON to `output_path`.

## Output

```json
{
  "site": "example.com",
  "audited_at": "2026-09-03T14:32:00Z",
  "crawl_meta": {
    "pages_crawled": 5,
    "pages_errored": 1,
    "errors": [{"url": "https://example.com/broken", "error": "ConnectionTimeout"}]
  },
  "summary": { "total_findings": 6, "critical": 1, "high": 2, "medium": 3 },
  "findings": [
    {
      "id": "F-001",
      "title": "GPTBot blocked in robots.txt",
      "severity": "critical",
      "gap_type": "indexing",
      "category": "discoverability",
      "url": "https://example.com/robots.txt",
      "evidence": "Directive 'Disallow: /' found under User-agent: GPTBot.",
      "suggested_action": {
        "summary": "Remove or relax the GPTBot disallow rule to allow AI crawler access.",
        "priority": "critical",
        "scope": "site"
      }
    }
  ]
}
```

`gap_type`: `"indexing"` | `"citation"` | `"engagement"`
`scope` (in `suggested_action`): `"page"` | `"site"` | `"brand"`