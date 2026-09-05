---
name: engagement-audit
description: Audits a website's DOM for structural orientation and context retention, diagnosing the underlying reasons why human visitors abandon the page.
license: Apache-2.0
---

# Engagement Audit

## When to use
Use this skill when diagnosing high bounce rates or poor on-site engagement. It evaluates the semantic hierarchy and readability of the raw DOM to ensure a visitor is instantly oriented upon arrival.

## Inputs
* `url`: The target website URL (e.g., `https://example.com`).

## Procedure
1. Receive the target URL.
2. Extract the raw DOM payload.
3. Evaluate structural orientation by analyzing the semantic heading hierarchy (e.g., presence and uniqueness of `<h1>`).
4. Assess context retention by checking for overwhelming, unbroken blocks of text without navigational breakers.
5. Output findings prioritized by their impact on user retention.

## Output
A JSON array of findings. Each finding includes an `id`, `title`, `severity` (critical, high, medium), `evidence` extracted directly from the DOM, and a `suggested_action` for remediation.