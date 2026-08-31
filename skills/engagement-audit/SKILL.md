---
name: engagement-audit
description: Audits post-click context retention, deep-fragment anchors, conversational referrer routing, and cross-category vector isolation.
license: Apache-2.0
allowed-tools:
  - dom-parser
  - url-analyzer
  - script-inspector
---

# Engagement & Context Retention Audit

## When to use
Diagnose high bounce from AI referrals and semantic attribute conflation across catalog lines.

## Inputs
* `url` (string, required): Page URL.
* `page_data` (dict, optional): Pre-fetched crawl data.

## Procedure
1. **Deep Semantic Anchors**:
   * Inspect element `id` attributes for high-intent patterns: `specs`, `pricing`, `features`, `materials`, `reviews`, `availability`, `buy`.
   * Flag absence on product-like pages as `medium`.
2. **Conversational Referrer Readiness**:
   * Scan inline `<script>` blocks for `document.referrer`, `chatgpt`, `perplexity`, `claude`, `intent-bridge`.
   * Scan raw HTML for CSS class/id patterns: `ai-banner`, `intent-bridge`, `assistant-context`.
   * Inspect response headers for Edge worker signatures (`cf-worker`, `x-fastly-ttl`, `x-vercel-id`).
   * If none detected, flag `medium` context-severance risk.
3. **Cross-Category Bleed** (site-wide):
   * Build map: URL directory prefix → set of `category` schema values.
   * If one prefix maps to multiple categories, flag `medium` semantic bleed.
4. **Orientation Signal**:
   * Product pages should have a descriptive `h1` and immediate price/spec visibility.
   * Flag generic/missing `h1` as `medium`.

## Output
Finding records with `category: "engagement"`.
