---
name: crawl-render-audit
description: Audits crawler accessibility, rendering barriers, structured data coverage, and machine-readable manifest endpoints.
license: Apache-2.0
allowed-tools:
  - web-fetch
  - dom-parser
---

# Crawl & Render Audit

## When to use
Diagnose why a brand is omitted from AI assistant retrieval.

## Inputs
* `url` (string, required): Page URL.
* `page_data` (dict, optional): Pre-fetched `{status, headers, parser, has_framework, has_ui_bridge}`.

## Procedure
1. **Triple-Layer Crawler Gate**:
   * `robots.txt`: `RobotFileParser.can_fetch()` for AI tokens (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Bytespider`, `CCBot`, `anthropic-ai`).
   * `<meta name="robots">`: flag `noindex` / `none` as `critical`.
   * `X-Robots-Tag` header: flag `noindex` as `critical`.
2. **CSR Wall**: If static text `< 150` words and scripts `> 40KB`, flag `high`. Strengthen evidence with framework hydration markers found in raw HTML.
3. **Semantic Structure**: Flag missing `<main>` / `<article>` as `medium`. Flag 0 or `> 1` `h1` as `medium`.
4. **Schema.org JSON-LD**:
   * Absence of any JSON-LD → `high`.
   * E-commerce text signals without `Product` / `Offer` schema → `high`.
   * Missing `BreadcrumbList` or `SpeakableSpecification` → `medium`.
   * Missing `WebSite` schema **on root only** → `medium`.
5. **Machine-Readable Manifest**: `GET /llms.txt` and `/llms-full.txt`. Flag missing or malformed (not starting with `#` or `< 50` bytes) as `medium`.
6. **Open Graph**: Flag missing `og:title` or `og:description` as `medium`.

## Output
Finding records with `category: "discoverability"`.
