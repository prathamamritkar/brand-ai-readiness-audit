---
name: engagement-audit
description: >
  Evaluates page engagement capability by analyzing structural orientation, context retention, accessibility, and readability. Checks for heading hierarchies, semantic landmarks, text density, visual breaks, and language definitions to ensure both human visitors and AI systems can process and understand the content.
license: Apache-2.0
---

# Engagement Audit

## When to use
Use this skill to determine whether a web page effectively holds visitor attention and provides clear navigational structure and text layout.

## Inputs
- `url`: The URL of the web page to analyze.

## Procedure
1. **Phase A — Structural Orientation**: Analyzes `<h1>` tags, heading hierarchies, and semantic landmarks.
2. **Phase B — Context Retention**: Checks lead paragraph answer density, walls-of-text, structural breakers, and language definition.
3. **Phase C — Accessible Context**: Identifies unlabeled interactive elements and missing mobile optimization tags.

## Output format
A JSON list of finding objects, matching this schema:
```json
{
  "id": "ENG-NNN",
  "title": "Issue Title",
  "severity": "critical|high|medium",
  "evidence": "Concrete proof from DOM",
  "suggested_action": {
    "summary": "Specific fix with mechanism explanation",
    "priority": "critical|high|medium"
  }
}
```