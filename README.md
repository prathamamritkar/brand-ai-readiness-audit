# Brand AI Readiness Audit

An `agentskills.io`-compliant Agent Skill Marketplace for auditing public websites for AI discoverability, machine readability, entity trust, knowledge freshness, and conversational engagement.

The marketplace uses a single orchestrator entrypoint and four focused domain skills. It diagnoses evidence-backed visibility gaps and produces actionable, provider-neutral recommendations with benchmark metrics without modifying the target website.

## Architecture

```
[Public Website URL]
        │
        ▼
audit-orchestrator (Entrypoint)
        │
        ├── BFS Crawl (robots.txt, crawl-delay, max-pages, timeout)
        │
        ├── crawl-render-audit      → "Can AI crawlers fetch, parse, and render content?"
        ├── entity-trust            → "Can AI models disambiguate and trust brand identity?"
        ├── freshness-corroboration  → "Are facts current, corroborated, and canonical?"
        └── engagement-audit        → "Can AI and humans navigate and extract key answers?"
        │
        ▼
Severity Correlation & Boosting Engine
        │
        ▼
Structured JSON Audit Report (with AI Readiness Score)
```

## Skills

| Skill | Type | Responsibility |
|---|---|---|
| `audit-orchestrator` | Entrypoint | Bounded BFS crawl, dispatches domain checks, correlates cross-skill signals, boosts severities, and emits the final JSON audit report. |
| `crawl-render-audit` | Domain | Audits AI crawler access (robots.txt ACLs, WAF/CAPTCHA bot-blocks), HTTPS transport, CSR hydration barriers, semantic HTML, text extraction density, `/llms.txt`, and image alt-text coverage. |
| `entity-trust` | Domain | Audits Schema.org structured data, stable `@id` anchoring, authoritative `sameAs` links (Wikidata, Wikipedia, LinkedIn), disambiguating descriptions, brand name consistency, offering schemas, entity relationships, and legal disclosures. |
| `freshness-corroboration` | Domain | Audits temporal markers (`dateModified`, `Last-Modified`, stale copyright years), sitemap declaration & `<lastmod>`, canonical drift, and legacy URL tombstones. |
| `engagement-audit` | Domain | Audits on-site retention, heading hierarchy gaps, lead answer density, wall-of-text scannability, section fragment anchors (`#id`), transactional CTAs, and cross-category taxonomy bleed. |

## Guardrails

- **Read-only**: Strictly non-intrusive. Zero site modifications, zero authenticated access.
- **Respectful**: Honors `robots.txt`, `Crawl-delay` (capped at 5 s per request to prevent budget bleed), and `noindex`/`none` directives.
- **Bounded**: Enforces a strict 280-second hard ceiling (under the 300-second competition ceiling) and configurable page budget (default: 5 pages).
- **Generalized**: Pattern-driven heuristics without hardcoded brand names, pricing assumptions, or CMS biases.
- **Calibrated Scoring**: Emits an executive `ai_readiness_score` (0–100), headline, top priority, and phase verdicts alongside raw findings.

## Execution

### Run the Audit

```bash
python skills/audit-orchestrator/scripts/audit_engine.py --url https://example.com --max-pages 5 --out report.json
```

Options:
- `--url`: Target website URL (required)
- `--max-pages`: Maximum internal pages to crawl (default: 5)
- `--timeout`: Per-request network timeout in seconds (default: 15)
- `--out`: Path to write report JSON file (optional, defaults to stdout)

### Validation

Validate the marketplace entrypoint directly against any target URL:

```bash
python skills/audit-orchestrator/scripts/audit_engine.py --url https://example.com --max-pages 1
```

All 5 skills adhere strictly to the `agentskills.io` specification with dedicated `SKILL.md` instructions and bundled execution scripts.

## Output Schema

The engine emits a severity-ranked, machine-readable JSON report:

```json
{
  "site": "example.com",
  "audited_at": "2026-09-13T23:30:00Z",
  "crawl_meta": {
    "pages_crawled": 5,
    "pages_errored": 0,
    "errors": []
  },
  "summary": {
    "ai_readiness_score": 82,
    "headline": "example.com has solid AI readiness with 6 optimization opportunities.",
    "top_priority": "Add Organization JSON-LD with name, url, logo, sameAs, and disambiguatingDescription.",
    "total_findings": 6,
    "critical": 0,
    "high": 2,
    "medium": 4,
    "phase_verdicts": {
      "crawl_render": "pass",
      "entity_trust": "warn",
      "freshness": "pass",
      "engagement": "pass"
    }
  },
  "findings": [
    {
      "id": "F-001",
      "title": "Machine-Readable Organization Identity Missing",
      "severity": "high",
      "category": "entity_identity",
      "url": "https://example.com",
      "evidence": "Visible site content present but no Organization, Brand, or LocalBusiness JSON-LD found.",
      "suggested_action": {
        "summary": "Add Organization JSON-LD with name, url, logo, sameAs, and disambiguatingDescription.",
        "priority": "high",
        "scope": "site"
      }
    }
  ]
}
```

## Marketplace Structure

```
brand-ai-readiness-audit/
├── marketplace.json
├── README.md
├── LICENSE
├── CONTRIBUTORS.md
└── skills/
    ├── audit-orchestrator/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── audit_engine.py
    │   └── references/
    │       ├── severity_rubric.md
    │       ├── remediation_catalog.md
    │       └── checklist.md
    ├── crawl-render-audit/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── analyze_crawl_render.py
    ├── entity-trust/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── analyze_entity.py
    ├── freshness-corroboration/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── analyze_freshness.py
    └── engagement-audit/
        ├── SKILL.md
        └── scripts/
            └── analyze_engagement.py
```
