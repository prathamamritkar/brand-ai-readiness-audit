---
name: freshness-corroboration
description: Audits temporal signals, cross-web entity corroboration, canonical drift, and stale URL pollution. Identifies citation gaps where AI assistants surface outdated or ambiguous brand facts, and indexing gaps from canonical inconsistency.
license: Apache-2.0
allowed-tools:
  - python-runtime
---

# Freshness & Corroboration Audit

## When to use
Diagnose why AI assistants surface outdated brand facts, attribute claims to the wrong entity, or quote a product or price that no longer exists.

## Inputs
* `url` (string, required): Page URL.
* `page_data` (dict): `{status_code, headers, html, word_count}` from the orchestrator crawl.

## Procedure

If `page_data` is absent or `status_code` is not 2xx, skip all checks for this URL.

### Temporal Signals (`gap_type: "citation"`)

1. **Date marker presence**: Check HTTP `Last-Modified` response header and, within valid JSON-LD blocks, `dateModified` and `datePublished` fields. If both are absent on a content page (`word_count > 150` or a non-empty `<h1>` is present), flag `medium`. Evidence: state which signals were probed and what each returned. Do not flag on pages that appear to be navigation-only (word count < 50).

2. **Stale date signal**: If `dateModified` or `Last-Modified` is present and is more than 365 days in the past, and the page contains pricing or product availability signals (currency symbols, stock phrases), flag `medium`. A stale date on a product page is a strong indicator that AI assistants will surface outdated facts. Evidence: report the date found and its age.

### Entity Corroboration (`gap_type: "citation"`)

3. **Knowledge graph anchors**: Locate JSON-LD blocks where `@type` is `Organization` or `Brand`. If found:
   - Check for a `sameAs` field containing at least one external URL (not the same domain). If absent or empty → `medium`. Suggested action: add `sameAs` links to Wikidata, Wikipedia, LinkedIn, or Crunchbase entries for the brand. Scope: `brand`.
   - Do not apply these checks to `Product`, `Article`, or other page-level types — entity anchoring is a brand-level concern.
   - If JSON-LD is malformed (parse failure), skip gracefully — `crawl-render-audit` already flags this.
   - Note: `disambiguatingDescription` presence is audited by `entity-trust`, not this skill.

4. **Cross-web corroboration gap** (emitted once per audit by orchestrator, not per page): If no `sameAs` links referencing external authority domains are found across any crawled page, emit one site-scoped `medium` recommendation: the brand has no cross-web entity anchoring, making it vulnerable to AI misattribution. Scope: `brand`.

### Canonical Drift (`gap_type: "indexing"`)

5. **Canonical self-reference drift**: If `<link rel="canonical">` points to a URL on a different domain than the current page, flag `medium` — authority is being assigned elsewhere. If it points to the same domain but a materially different path (not just trailing slash normalization), flag `medium`. Evidence: report canonical href vs current URL. Skip if canonical is absent (already covered by `crawl-render-audit`).

### Stale URL Pollution (`gap_type: "citation"`)

6. **Inferred legacy URL probes**: From the set of URLs crawled, extract path-segment patterns. For each distinct path pattern, construct at most 2 plausible retired-path variants by appending or prepending common archival signals (`/old`, `-v1`, `/archive`, `/deprecated`) to the last non-numeric segment. Issue HEAD requests (5 s timeout each). If any variant returns HTTP 200, flag `medium` — an active legacy URL may feed AI assistants stale facts about a product or page that has moved. Evidence: list each probed URL and its status code. If fewer than 3 pages were crawled (insufficient pattern basis), skip this check entirely and note in `crawl_meta`.

## Output
Finding records. `gap_type`: `"citation"` or `"indexing"`. `category`: `"discoverability"`.
