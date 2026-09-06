---
name: audit-orchestrator
description: >
  The designated entrypoint for the Brand AI-Readiness Audit marketplace.
  Fetches the target URL plus up to 5 internal pages, then orchestrates
  four sub-skills in strict diagnostic order — crawl-render, discoverability,
  freshness, engagement — to produce a unified, severity-sorted multi-page
  audit report with prose summary and phase-level verdicts.
license: Apache-2.0
---

# Audit Orchestrator

## When to use
Use this skill as the **sole entrypoint** to audit a target website for AI discoverability and on-site engagement problems. It composes four focused sub-skills into a single diagnostic report spanning multiple pages.

## Inputs
* `url`: The target website URL (e.g., `https://example.com`).
* `--pages N` (optional): Maximum internal pages to crawl beyond the target. Default: 5.
* `--single` (optional): Single-page mode — skips internal link crawling.

## Procedure
1. Receive the target URL.
2. **Primary Fetch** — fetch the URL and its robots.txt via `utils/fetcher.py`.
3. **Link Discovery** — extract up to 5 same-domain internal links from the DOM.
4. **Multi-Page Fetch** — fetch each internal page (lightweight, reuses robots parser).
5. **For each page**, run all 4 sub-skills in strict diagnostic order:
   - Phase 1 — Crawl & Render (can AI reach the content?)
   - Phase 2 — Discoverability (can AI identify the brand?)
   - Phase 3 — Freshness (can AI trust the content?)
   - Phase 4 — Engagement (will visitors stay?)
6. **Deduplicate** — merge duplicate findings across pages with page attribution.
7. **Phase Verdicts** — compute pass/warn/fail per audit phase.
8. **AI Readiness Score** — compute weighted composite score (0–100).
9. **Prose Summary** — generate human-readable headline and top priority.
10. **Compose** — severity-sort findings, emit the final report.

## Output
A strict JSON object matching the mandatory marketplace schema:
```json
{
  "site": "...",
  "audited_at": "ISO-TIMESTAMP",
  "pages_crawled": 6,
  "pages": ["https://example.com", "..."],
  "summary": {
    "ai_readiness_score": 72,
    "total_findings": 0,
    "critical": 0, "high": 0, "medium": 0,
    "headline": "Human-readable narrative summary.",
    "top_priority": "The single most impactful fix.",
    "phase_verdicts": {
      "crawl_render": "pass|warn|fail",
      "discoverability": "pass|warn|fail",
      "freshness": "pass|warn|fail",
      "engagement": "pass|warn|fail"
    }
  },
  "findings": [ ... ]
}
```