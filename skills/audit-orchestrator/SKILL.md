---
name: audit-orchestrator
description: The designated entrypoint for the Brand AI-Readiness Audit marketplace. Orchestrates the discoverability and engagement skills to produce a unified, prioritized report.
license: Apache-2.0
---

# Audit Orchestrator

## When to use
Use this skill as the primary entrypoint to audit a target website. It strictly controls the order of data execution and presentation, ensuring the AI agent receives a cohesive diagnostic report rather than disjointed facts.

## Inputs
* `url`: The target website URL (e.g., `https://example.com`).

## Procedure
1. Receive the target URL.
2. Execute `discoverability-audit` to extract underlying AI visibility mapping standards.
3. Execute `engagement-audit` to diagnose human structural orientation.
4. Aggregate the JSON responses from both skills.
5. Calculate the summary of findings (total, critical, high, medium).
6. Format and emit the final report matching the mandatory marketplace schema.

## Output
A strict JSON object containing `site`, `audited_at`, a `summary` of finding severity counts, and a combined `findings` array containing all evidence and suggested actions.