# Brand AI Readiness Audit

An Agent Skill Marketplace for auditing public websites for AI discoverability, machine readability, entity trust, freshness, and conversational engagement.

The marketplace uses a single orchestrator and modular specialist skills that share a structured evidence bundle. It identifies evidence-backed issues and produces actionable, provider-neutral recommendations without modifying the target website.

## Architecture

Public Website URL
        |
        v
site-intelligence
        |
        +--> machine-readability
        +--> engagement-audit
        +--> crawl-render-audit
        +--> freshness-corroboration
        +--> entity-trust
        |
        v
evidence-correlator
        |
        v
recommendation-engine
        |
        v
Final Audit Report

## Skills

- audit-orchestrator — single entrypoint coordinating the complete audit pipeline.
- site-intelligence — performs bounded, same-origin, read-only website discovery and produces the shared evidence bundle.
- machine-readability — evaluates structured and semantic signals that help automated systems interpret website content.
- engagement-audit — evaluates discoverable navigation, calls to action, and engagement pathways.
- crawl-render-audit — evaluates content observability, semantic structure, and rendering-related limitations.
- freshness-corroboration — evaluates publication and modification signals and corroborates freshness evidence.
- entity-trust — evaluates organization, offering, and identity signals for consistency and machine interpretation.
- evidence-correlator — combines explicit specialist findings, evaluates evidence sufficiency, and reduces unsupported false positives.
- recommendation-engine — converts supported findings into prioritized, provider-neutral recommendations with verification steps.

## Design Principles

- Evidence first: observations are separated from findings.
- Modular: each skill has a focused responsibility and shared contracts.
- Read-only: the target website is analyzed without modification.
- Provider-neutral: recommendations do not depend on a specific CMS, framework, hosting provider, or AI platform.
- Conservative: uncertain or unavailable evidence is reported as a limitation rather than asserted as a defect.
- Deterministic: outputs and tests are designed for reproducible evaluation.
- Actionable: findings connect evidence to root causes, recommendations, expected outcomes, and verification steps.

## Audit Flow

1. Discover — site-intelligence collects bounded website evidence.
2. Analyze — specialist skills independently evaluate different dimensions of AI readiness.
3. Correlate — evidence-correlator combines explicit findings and evaluates evidence sufficiency.
4. Recommend — recommendation-engine converts supported findings into actionable recommendations.
5. Report — audit-orchestrator produces the final structured audit report.

## Running the Audit

From the repository root:

python skills\audit-orchestrator\scripts\run_audit.py https://example.com

The orchestrator collects site evidence, runs the specialist skills, correlates supported findings, generates recommendations, and produces the final audit report.

## Testing

Run the complete test suite:

Get-ChildItem -Path skills -Recurse -Filter "test_*.py" | ForEach-Object {
    python $_.FullName
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Current local regression status:

81/81 tests passing

## Marketplace Structure

marketplace.json
README.md
skills/
├── audit-orchestrator/
├── site-intelligence/
├── machine-readability/
├── engagement-audit/
├── crawl-render-audit/
├── freshness-corroboration/
├── entity-trust/
├── evidence-correlator/
└── recommendation-engine/

marketplace.json registers all nine skills, with audit-orchestrator as the designated entrypoint.

## Output

The audit produces a structured report containing:

- Audited site and crawl metadata
- Evidence-backed findings
- Affected scope and pages
- Evidence relationships and sufficiency
- Confidence levels
- Prioritized recommendations
- Verification steps
- Explicit limitations and uncertainty

The marketplace is designed to help AI agents understand what is wrong, why it matters, what evidence supports it, and what can be done next.
