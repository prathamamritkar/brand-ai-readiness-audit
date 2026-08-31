---
name: freshness-corroboration
description: Audits temporal signals, knowledge graph entity bindings, canonical consistency, and legacy URL tombstoning.
license: Apache-2.0
allowed-tools:
  - header-inspector
  - schema-validator
  - web-fetch
---

# Freshness & Corroboration Audit

## When to use
Diagnose why AI assistants surface outdated brand facts or discontinued products.

## Inputs
* `url` (string, required): Page URL.
* `page_data` (dict, optional): Pre-fetched crawl data.

## Procedure
1. **Temporal Signals**:
   * HTTP `Last-Modified` header.
   * Schema.org `dateModified` / `datePublished`.
   * If both absent on a content page (`h1` or `> 200` words), flag `medium`.
2. **Knowledge Graph Vectors**:
   * `Organization` / `Brand` JSON-LD must contain `sameAs` array linking to authority nodes (Wikidata, Wikipedia).
   * Must contain `disambiguatingDescription`.
   * Flag missing as `medium`.
3. **Canonical Consistency**:
   * Content pages must have `rel="canonical"` link tag.
   * Flag missing as `medium`.
4. **Legacy Tombstoning** (site-wide):
   * Probe heuristic legacy URL patterns (`-old`, `/archive/...`).
   * Any returning `HTTP 200` → `medium` stale-fact pollutant.
5. **Sitemap Freshness**:
   * Parse `/sitemap.xml` (handle `<sitemapindex>` and `<urlset>`).
   * If `> 50%` entries lack `<lastmod>`, flag `medium`.

## Output
Finding records with `category: "discoverability"`.
