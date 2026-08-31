---
name: audit-orchestrator
description: Entrypoint skill that ingests a domain URL, runs a bounded BFS crawl, dispatches deterministic GEO checks, and emits a severity-ranked JSON audit report.
license: Apache-2.0
metadata:
  entrypoint: true
  version: 2.1.0
allowed-tools:
  - python-runtime
  - web-fetch
  - filesystem-writer
---

# Audit Orchestrator

## When to use
Audit any public website for conversational AI visibility, entity freshness, and post-click retention.

## Inputs
* `url` (string, required): Target domain root.
* `max_pages` (integer, optional, default: `5`, max: `10`): Internal pages to sample.
* `output_path` (string, optional, default: `"audit_report.json"`).

## Procedure
1. **Initialize**: Normalize URL, record ISO 8601 UTC `audited_at`, start 280 s runtime budget.
2. **robots.txt**: Parse with `RobotFileParser`. Verify AI bots are not blocked. Extract `Crawl-delay`.
3. **Bounded BFS Crawl**: Fetch root + internal links up to `max_pages`. Respect `robots.txt` per-path rules. Enforce delay between requests.
4. **Dispatch Checks** (per page):
   * **Crawl & Render**: AI ACLs, CSR barrier, semantic landmarks, heading hierarchy, Schema.org (`Product`, `Offer`, `BreadcrumbList`, `SpeakableSpecification`, `WebSite` on root only), `/llms.txt`, Open Graph.
   * **Freshness & Corroboration**: `Last-Modified`, `dateModified`, `sameAs`, `disambiguatingDescription`, canonical tags.
   * **Engagement & Retention**: Deep semantic anchors (`#specs`, `#pricing`), inline-script referrer detection, intent-bridge UI patterns, Edge worker headers.
5. **Site-Wide Aggregation**:
   * Sitemap `/sitemap.xml` freshness (`<lastmod>` coverage, sitemap-index support).
   * Cross-category semantic bleed: map URL prefix → `category` schema values; flag if one prefix holds multiple categories.
   * Legacy tombstoning: probe 4 heuristic legacy URL variants; flag any returning `HTTP 200`.
6. **Correlate & Emit**: Map to `severity_rubric.md`, bind remediations from `remediation_catalog.md`, sort by severity, write JSON.

## Output
```json
{
  "site": "example.com",
  "audited_at": "2026-08-31T14:32:00Z",
  "summary": { "total_findings": 0, "critical": 0, "high": 0, "medium": 0 },
  "findings": [
    {
      "id": "F-001",
      "title": "...",
      "severity": "critical",
      "category": "discoverability",
      "url": "https://example.com/...",
      "evidence": "...",
      "suggested_action": { "summary": "...", "priority": "critical" }
    }
  ]
}
```