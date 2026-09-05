# Brand AI-Readiness Audit Marketplace

This Agent Skill Marketplace diagnoses the underlying reasons why a brand is invisible to AI assistants and why human visitors fail to engage. 

It strictly evaluates universal DOM mapping standards (like JSON-LD) and structural orientation metrics (semantic hierarchy, readability), explicitly avoiding hardcoded scraping paths.

## Composition
* `audit-orchestrator`: The entrypoint. It strictly orders the execution of sub-skills to optimize AI agent learning context and emits the final unified report.
* `discoverability-audit`: Evaluates the raw HTML payload against JS-rendered dependencies and searches for SEO hygiene standards to find why AI cannot map the entity.
* `engagement-audit`: Diagnoses semantic hierarchies and massive text blocks to determine why human context retention fails upon arrival.

## Execution
Run from the root directory:
`python skills/audit-orchestrator/scripts/run_audit.py https://example.com`