---
name: audit-orchestrator
description: Entry point for a website AI-readiness audit. Coordinates specialist skills, combines their evidence-backed findings, and emits the marketplace audit report. Use when an agent receives a website audit request.
license: MIT
---

# Audit Orchestrator

## Status

This is the designated marketplace entrypoint. The composition pipeline is being implemented incrementally.

## Current procedure

1. Accept a public website URL as the audit target.
2. Invoke `site-intelligence` to establish the shared site evidence bundle.
3. Preserve the evidence bundle as the common input contract for future specialist skills.
4. As additional specialist skills are added, compose their findings through the shared finding contract.
5. Emit one final audit report conforming to the marketplace-required schema.

## Safety

- Read-only auditing only.
- Never authenticate to a target site.
- Never modify target-site content.
- Respect `robots.txt`.
- Keep crawling bounded by the configured page and time budgets.