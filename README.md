# Brand AI-Readiness Audit Marketplace

An Agent Skill Marketplace that diagnoses the underlying reasons why a brand is invisible to AI assistants and why human visitors fail to engage. It audits any website — across diverse industry verticals and horizontals — using 35 evidence-backed heuristics covering all failure modes that separate cited brands from ignored ones.

**Recommend-only**: This marketplace strictly audits and reports. No skill ever alters a live site.

## Architecture

The marketplace decomposes the audit into **4 focused domain skills**, each answering a distinct diagnostic question, composed by a single **orchestrator entrypoint**:

```
audit-orchestrator (entrypoint)
  │
  ├─ 1. crawl-render-audit    → "Can AI crawlers reach and extract the content?"
  ├─ 2. discoverability-audit → "Can AI identify WHO this brand is?"
  ├─ 3. freshness-signals     → "Is the content trustworthy and temporally current?"
  └─ 4. engagement-audit      → "Will a human visitor stay and engage?"
```

### Execution Order (Deliberate)
The orchestrator runs skills in strict diagnostic order optimized for AI agent contextual learning:
1. **Crawl & Render** — establishes whether content is even reachable (foundational)
2. **Discoverability** — analyzes structured identity (builds on access)
3. **Freshness** — evaluates temporal trust (builds on identity)
4. **Engagement** — diagnoses human experience (meaningful only if content exists)

### Multi-Page Crawl
The orchestrator crawls the target URL **plus up to 5 internal pages** discovered via DOM link extraction. Findings are deduplicated across pages with attribution (e.g., `[Found on 4/6 pages crawled]`). Issues that exist on one specific page show the exact URL.

### Phase Verdicts
Each audit phase receives a verdict: **pass** (no high/critical findings), **warn** (high-severity issues), or **fail** (critical blockers). This gives judges and users an at-a-glance health check.

### Prose Summary
Every report includes a human-readable `headline` explaining the brand's AI readiness status and a `top_priority` identifying the single most impactful fix.

## Skills

### `audit-orchestrator` (entrypoint)
Orchestrates multi-page crawl, composes the four domain skills, deduplicates findings, computes phase verdicts, generates prose summary, sorts by severity, and emits the final unified report.

### `crawl-render-audit` (8 heuristics)
Covers: **Crawlability, JS-render gaps, Facts locked in non-text**
- AI crawler blocks via robots.txt (GPTBot, PerplexityBot, ClaudeBot, etc.)
- Meta robots noindex/nosnippet directives
- JS rendering dependency (word count analysis)
- Noscript fallback detection
- SSR framework detection (Next.js, Nuxt, React)
- Facts locked in images without substantive alt text
- Media embeds without text transcripts or VideoObject schema

### `discoverability-audit` (10 heuristics)
Covers: **Missing/invalid structured data, Entity ambiguity**
- JSON-LD presence and syntax validation
- Schema type coverage (generic vs. domain-specific)
- Entity disambiguation via `sameAs` links
- Stable entity anchoring via `@id`
- Canonical URL integrity
- Title, meta description, and Open Graph completeness
- Proactive: hreflang and BreadcrumbList schema

### `freshness-signals` (7 heuristics)
Covers: **Stale or uncorroborated facts**
- Machine-readable date markup (JSON-LD, `<time>`, meta, HTTP headers)
- Stale copyright year detection
- Outdated schema dates (> 2 years)
- Temporal contradiction across date sources
- Author/publisher attribution
- Proactive: FAQ/HowTo schema and sitemap declaration

### `engagement-audit` (10 heuristics)
Covers: **Weak on-site orientation, No context retention**
- Heading hierarchy integrity (h1 presence, level gaps)
- Semantic landmark presence (main, nav, header, footer)
- Lead answer density (front-loaded value proposition)
- Wall-of-text detection and scannability analysis
- Language declaration
- Unlabeled interactive elements
- Proactive: viewport meta tag for mobile

## Requirements

```
pip install requests beautifulsoup4
```

No external AI APIs. No headless browsers. Only `requests` + `beautifulsoup4` with Python's built-in `html.parser`.

## Execution

From the repository root:

```bash
# Full multi-page audit (crawls target + up to 5 internal pages)
python skills/audit-orchestrator/scripts/run_audit.py https://example.com

# Limit internal pages crawled
python skills/audit-orchestrator/scripts/run_audit.py https://example.com --pages 3

# Single-page mode (fastest)
python skills/audit-orchestrator/scripts/run_audit.py https://example.com --single

# Save report to file
python skills/audit-orchestrator/scripts/run_audit.py https://example.com > report.json
```

Each sub-skill also works independently:

```bash
python skills/crawl-render-audit/scripts/check_crawl_render.py https://example.com
python skills/discoverability-audit/scripts/check_discoverability.py https://example.com
python skills/freshness-signals/scripts/check_freshness.py https://example.com
python skills/engagement-audit/scripts/check_engagement.py https://example.com
```

## Output Schema

```json
{
  "site": "https://example.com",
  "audited_at": "2026-09-05T08:00:00Z",
  "pages_crawled": 4,
  "pages": ["https://example.com", "https://example.com/about", "..."],
  "summary": {
    "total_findings": 15,
    "critical": 1,
    "high": 6,
    "medium": 8,
    "headline": "example.com has 1 critical AI visibility failure that blocks crawlers.",
    "top_priority": "CRITICAL: Meta Robots Noindex — Remove noindex directive.",
    "phase_verdicts": {
      "crawl_render": "fail",
      "discoverability": "warn",
      "freshness": "pass",
      "engagement": "warn"
    }
  },
  "findings": [
    {
      "id": "CR-001",
      "title": "AI Crawlers Blocked via robots.txt",
      "severity": "critical",
      "evidence": "AI bots blocked: GPTBot, PerplexityBot. [Found on 4/4 pages crawled]",
      "suggested_action": {
        "summary": "Remove blocks for AI-specific user agents.",
        "priority": "critical"
      },
      "page": "4/4 pages"
    }
  ]
}
```