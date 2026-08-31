# Brand AI-Readiness Audit Marketplace

An `agentskills.io`-compliant, deterministic, read-only Agent Skill for auditing any public website's AI discoverability, knowledge graph freshness, and conversational engagement readiness.

## 1. Architecture

Decomposes audit logic into three domain sub-skills coordinated by one entrypoint:

| Skill | Responsibility |
|-------|----------------|
| `audit-orchestrator` | Entrypoint. Bounded BFS crawl, dispatches checks, deduplicates findings, emits JSON. |
| `crawl-render-audit` | Off-site discoverability: crawler ACLs, CSR walls, semantic HTML, Schema.org, `/llms.txt`, Open Graph. |
| `freshness-corroboration` | Knowledge graph drift: temporal markers, `sameAs` vectors, canonicals, legacy tombstoning. |
| `engagement-audit` | On-site retention: deep anchors, referrer handling, intent-bridge UI, category bleed. |

## 2. Orchestration

```
[Target URL]
  → audit-orchestrator
      → BFS crawl (respects robots.txt, max_pages, crawl-delay)
      → Per-page: crawl-render + freshness + engagement checks
      → Site-wide: sitemap, taxonomy bleed, legacy probes
      → JSON report
```

## 3. Guardrails

- **Read-only**: Zero mutations, zero auth.
- **Respectful**: Honors `robots.txt`, `Crawl-delay`, `noindex`.
- **Bounded**: Hard timeout **280 s** (under the 5-minute ceiling). Max 10 pages.
- **Generalized**: Pattern-driven. No hardcoded brands, prices, or CMS assumptions.

## 4. Execution

```bash
python3 skills/audit-orchestrator/scripts/audit_engine.py \
  --url https://example.com \
  --max-pages 5 \
  --out report.json
```

## 5. Layout

```
brand-ai-readiness-audit/
├── marketplace.json
├── README.md
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
    │   └── SKILL.md
    ├── freshness-corroboration/
    │   └── SKILL.md
    └── engagement-audit/
        └── SKILL.md
```
