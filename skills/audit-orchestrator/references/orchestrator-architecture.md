# Audit Orchestrator — Architecture Reference

## Pipeline Overview

The orchestrator executes a **multi-page diagnostic pipeline** in 11 steps:

```
Fetch Primary → Discover Links → Fetch Internal Pages
    ↓
Run 4 Skills × N Pages → Deduplicate → Sort → Score → Verdicts → Prose → Report
```

## Diagnostic Order (Deliberate)

Skills run in strict order optimized for diagnostic context building:

| Order | Skill | Question Answered | Rationale |
|-------|-------|-------------------|-----------|
| 1 | Crawl & Render | Can AI reach the content? | Foundational — all other checks are meaningless if crawlers can't access the page |
| 2 | Discoverability | Can AI identify WHO this brand is? | Builds on access — requires parseable DOM |
| 3 | Freshness | Is the content temporally trustworthy? | Builds on identity — dates corroborate entity claims |
| 4 | Engagement | Will a human visitor stay? | Meaningful only if content exists and is reachable |

## Multi-Page Crawl Strategy

1. **Primary page** is fetched with full robots.txt parsing
2. Up to **5 internal links** are extracted from the DOM (same-domain, HTTP(S), HTML resources only)
3. Internal pages use **lightweight fetch** — reuses the primary page's robots parser to avoid redundant robots.txt requests
4. Findings are **deduplicated** across pages using a composite key (`id + evidence_hash`) to preserve distinct findings that share the same ID

## AI Readiness Score Algorithm

The composite score starts at 100 and deducts based on severity:

| Severity | Points Deducted | Rationale |
|----------|----------------|-----------|
| Critical | −25 | Complete blocker (e.g., robots.txt blocks AI crawlers) |
| High | −10 | Significant gap (e.g., no structured data, no sameAs) |
| Medium | −3 | Optimization opportunity (e.g., missing noscript fallback) |

Score is clamped to [0, 100]. Interpretation:
- **90–100**: Excellent AI readiness
- **70–89**: Good, with optimization opportunities
- **50–69**: Significant gaps limiting AI visibility
- **0–49**: Critical failures blocking AI discovery

## Phase Verdicts

Each audit phase receives a verdict:
- **pass**: No high or critical findings in this phase
- **warn**: At least one high-severity finding
- **fail**: At least one critical-severity finding

## Error Handling

- **Unreachable URL**: Returns `ORCH-001` with score 0 and all phases set to "fail"
- **Sub-skill crash**: Wrapped in `_run_skill()` try/except — returns `<skill>-ERR` finding instead of crashing the pipeline
- **Finding validation**: All findings pass `_validate_finding()` — malformed findings are silently dropped

## Finding Schema

Every finding follows this strict contract:

```json
{
  "id": "CR-001",
  "title": "Human-readable title",
  "severity": "critical|high|medium",
  "evidence": "Specific evidence from the DOM...",
  "suggested_action": {
    "summary": "What to do about it",
    "priority": "critical|high|medium"
  },
  "page": "https://example.com (or '3/5 pages')"
}
```
