---
name: engagement-audit
description: Audits post-click context retention, page orientation, referrer-awareness patterns, conversion path visibility, and semantic category isolation. Identifies engagement gaps where AI-referred visitors arrive but immediately disengage.
license: Apache-2.0
allowed-tools:
  - python-runtime
---

# Engagement & Context Retention Audit

## When to use
Diagnose high bounce from AI referrals. Run after `crawl-render-audit` confirms the page is reachable and machine-readable.

## Inputs
* `url` (string, required): Page URL.
* `page_data` (dict): `{url, html, word_count, headers}` from the orchestrator crawl.
* `all_pages_schema` (list, optional): Aggregated schema data from all crawled pages, used for cross-category bleed check. Pass only when calling from orchestrator for site-wide aggregation.

## Procedure

All findings use `gap_type: "engagement"` and `category: "engagement"`. If `page_data` is absent or `status_code` is not 2xx, skip all checks.

1. **Page orientation signal**: A visitor who arrives from an AI referral needs immediate context. Check that `<h1>` is present (absence already flagged by `crawl-render-audit` — do not duplicate). Check that `<h1>` text is not identical to `<title>` with no additional information, and is not purely the brand or site name. If it provides no distinguishing context for the specific page → `medium`. Evidence: report the `<h1>` and `<title>` text found. Only flag on content pages (`word_count > 200`).

2. **Deep semantic anchors**: Count elements with an `id` attribute across the full HTML. On content/product pages (`word_count > 300`), fewer than 2 `id`-bearing elements → `medium` — AI assistants cannot deep-link users to specific facts, increasing bounce. Evidence: report count of `id`-bearing elements. Do not require specific `id` names; presence is the signal.

3. **Conversational referrer readiness**: Scan all inline `<script>` blocks (blocks without a `src` attribute) for evidence of referrer-awareness. Look for: the string `document.referrer`, query parameter parsing patterns (e.g. `URLSearchParams`, `location.search`), or session/local storage reads. If no referrer-awareness pattern is detected, scan HTML attributes and class names for any intent-bridge pattern (any class or id containing substrings like `referr`, `context`, `intent`, `assistant`). If nothing is found on a page that has structured data or is linked from the root navigation, flag `medium`. Evidence: report which signals were checked and what was found. Scope: page. Do not flag on every page — infer AI-referral likelihood from page type.

4. **Conversion path visibility**: Parse the document body. Find all `<a>` and `<button>` elements. For each, check if the visible text (stripped) or `aria-label` matches transactional intent: words such as "buy", "order", "get", "download", "contact", "start", "try", "sign up", "request", "book" (case-insensitive substring match). Determine the relative vertical position of the first such element by counting preceding block-level elements as a proxy for DOM depth. If no transactional element is found on a product or service page → `medium`. If the first transactional element is in the bottom 40% of the DOM → `medium`. Evidence: report text and position of first transactional element found, or "none found."

5. **`noscript` content divergence**: If a `<noscript>` block is present, compare its stripped text word set to the main body word set (excluding `<script>` and `<style>` content). If overlap is less than 50% of the `noscript` word set, flag `medium` — AI agents that do not execute JavaScript see a materially different page, which can cause a mismatch between the AI's description and what a non-JS visitor experiences. Evidence: report approximate overlap percentage.

6. **Cross-category semantic bleed** (site-wide, invoked by orchestrator with `all_pages_schema`): Build a map of URL path prefix (first path segment, e.g. `/products`, `/blog`) → set of distinct Schema.org `@type` or `category` values found across all pages under that prefix. If one prefix maps to more than one distinct product or content category type, flag `medium`. Evidence: list the prefix and the conflicting type values found. Handle gracefully: if fewer than 3 pages have valid schema, skip this check and note it in evidence.

## Output
Finding records. `gap_type`: `"engagement"`. `category`: `"engagement"`.
