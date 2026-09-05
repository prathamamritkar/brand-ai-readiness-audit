---
name: audit-orchestrator
description: >
  The designated entrypoint for the Brand AI-Readiness Audit marketplace.
  Fetches the target URL once, then orchestrates four sub-skills in strict
  diagnostic order — crawl-render, discoverability, freshness, engagement —
  to produce a unified, severity-sorted audit report. The execution order
  is deliberate: foundational access checks first, then identity, then trust,
  then human experience.
license: Apache-2.0
---

# Audit Orchestrator

## When to use
Use this skill as the **sole entrypoint** to audit a target website for AI discoverability and on-site engagement problems. It composes four focused sub-skills into a single diagnostic report.

## Inputs
* `url`: The target website URL (e.g., `https://example.com`).

## Procedure
1. Receive the target URL.
2. **Single Fetch** — fetch the URL and its robots.txt exactly once via `utils/fetcher.py`.
3. **Phase 1 — Crawl & Render** — execute `crawl-render-audit` to determine if AI crawlers can reach and extract the content.
4. **Phase 2 — Discoverability** — execute `discoverability-audit` to evaluate structured data and entity identity.
5. **Phase 3 — Freshness** — execute `freshness-signals` to assess temporal trust and corroboration.
6. **Phase 4 — Engagement** — execute `engagement-audit` to diagnose human orientation and retention.
7. **Compose** — aggregate all findings, sort by severity (critical → high → medium), calculate summary counts, emit the final report.

## Output
A strict JSON object matching the mandatory marketplace schema:
```json
{
  "site": "...",
  "audited_at": "ISO-TIMESTAMP",
  "summary": { "total_findings": 0, "critical": 0, "high": 0, "medium": 0 },
  "findings": [ ... ]
}
```