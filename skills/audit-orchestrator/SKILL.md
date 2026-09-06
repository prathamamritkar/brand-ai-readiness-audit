---
name: audit-orchestrator
description: Entry point for a website AI-readiness audit. Coordinates site evidence collection, specialist audit skills, evidence correlation, and recommendations into one final report. Use when an agent receives a public website audit request.
license: MIT
---

# Audit Orchestrator

## Purpose

The Audit Orchestrator is the single marketplace entrypoint for a public website AI-readiness audit.

It coordinates specialist skills without duplicating their audit logic.

The orchestrator is responsible for:

- Accepting the audit target
- Establishing shared site evidence
- Invoking specialist skills in dependency order
- Preserving evidence and provenance
- Handling unavailable specialist outputs gracefully
- Correlating findings
- Generating actionable recommendations
- Emitting one deterministic final audit report

## Execution Pipeline

Execute the audit in this order:

```text
Public Website URL
        ↓
site-intelligence
        ↓
┌────────────────────────────────────┐
│ Independent specialist audits      │
│ machine-readability                │
│ engagement-audit                   │
│ crawl-render-audit                 │
│ freshness-corroboration            │
│ entity-trust                       │
└──────────────────┬─────────────────┘
                   ↓
        evidence-correlator
                   ↓
        recommendation-engine
                   ↓
             Final Report