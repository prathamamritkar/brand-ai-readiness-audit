# Brand AI Readiness Audit

An Agent Skill Marketplace for auditing website AI discoverability and on-site engagement.

## Current status

This repository is being developed incrementally. The current implementation establishes the marketplace contract and the first evidence-collection skill.

## Skills

- `audit-orchestrator` — designated entrypoint; currently defines the composition contract.
- `site-intelligence` — crawls a public website in a bounded, read-only manner and produces structured site evidence for downstream skills.

## Development

The marketplace is designed around a shared evidence bundle. Specialist skills will consume that evidence rather than independently crawling the target site.

Current development is intentionally incremental so each milestone remains reviewable and testable.
