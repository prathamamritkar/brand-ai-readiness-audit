# Engagement Audit Checklist

## Phase A: Structural Orientation
1. **Missing Primary `<h1>` (ENG-001)**
   - *Why it matters*: Without an h1, AI agents and screen readers can't identify the primary topic.
   - *What good looks like*: One descriptive `<h1>` tag indicating the central topic.

2. **Conflicting `<h1>` Hierarchy (ENG-002)**
   - *Why it matters*: Multiple primary headings dilute semantic meaning.
   - *What good looks like*: A single `<h1>` tag with logically nested subheadings.

3. **Heading Level Gaps (ENG-003)**
   - *Why it matters*: Skipping heading levels breaks semantic outlining.
   - *What good looks like*: Sequential levels (e.g., h1 to h2, h2 to h3).

4. **No Semantic Landmarks (ENG-004)**
   - *Why it matters*: Missing landmarks like `<main>` and `<nav>` provide poor wayfinding context.
   - *What good looks like*: Structured layout with modern semantic elements.

## Phase B: Context Retention
5. **Weak Lead Answer Density (ENG-005)**
   - *Why it matters*: Dense or overly thin introductory paragraphs cause high bounce rates and fail to immediately address AI/human inquiries.
   - *What good looks like*: 20-120 words front-loading the page's value proposition.

6. **Wall-of-Text Paragraphs (ENG-006)**
   - *Why it matters*: Heavy blocks of text fatigue users and cause bounces.
   - *What good looks like*: Short paragraphs under 150 words.

7. **Low Scannability (ENG-007)**
   - *Why it matters*: Lengthy text without breakers prevents scanning.
   - *What good looks like*: Frequent use of lists, quotes, tables, or subheadings.

8. **No Language Declaration (ENG-008)**
   - *Why it matters*: Lack of explicit language attributes impedes text processing systems.
   - *What good looks like*: `<html>` tag with an explicit `lang` attribute.

## Phase C: Accessible Context
9. **Unlabeled Interactive Elements (ENG-009)**
   - *Why it matters*: Buttons/links without text or aria-labels trap screen readers and are meaningless to bots.
   - *What good looks like*: Clear descriptive text or `aria-label` attributes on every interactive node.

10. **Missing Viewport Meta (ENG-010)**
    - *Why it matters*: Lack of mobile optimization causes massive drop-offs for non-desktop traffic.
    - *What good looks like*: Proper `<meta name="viewport">` declaration.
