---
name: engagement-audit
description: Analyze observable website engagement and navigation signals from a Site Intelligence evidence bundle, including calls to action, internal pathways, contextual links, and page-level next actions. Use this skill when evaluating how clearly a public website exposes meaningful engagement paths to visitors and machines.
---

# Engagement Audit

## Purpose

Analyze observable engagement and navigation signals in a website's evidence bundle.

This skill identifies how pages expose meaningful next actions, internal pathways, calls to action, and contextual navigation.

This skill is observation-focused. It must not assign an overall engagement score, diagnose final root causes, or prescribe fixes.

## Input

Consume the Site Intelligence Evidence Bundle.

Expected input:

- Site metadata
- Crawl metadata
- Page records
- Page URLs and types
- Titles and headings
- Visible text
- Internal and external links
- Link anchor text when available
- Page depth and discovery provenance

Do not crawl the website independently when the required evidence is already present in the bundle.

## Analysis Areas

### 1. Calls to Action

Identify observable action-oriented signals such as:

- Contact
- Request a demo
- Get started
- Buy
- Subscribe
- Sign up
- Download
- Book
- Learn more
- View pricing
- Start a trial

Record the observed wording and source page.

Do not assume that every page requires a call to action.

### 2. Navigation Pathways

Identify meaningful internal pathways between pages.

Examples:

- Homepage → Product
- Product → Pricing
- Product → Documentation
- Service → Contact
- Article → Related Article
- Product → Case Study

Record the source page, destination URL, and available anchor text.

Do not infer user intent when the evidence does not support it.

### 3. Contextual Links

Identify links that provide meaningful context or continuation, including:

- Related content
- Documentation
- Product information
- Services
- Case studies
- Resources
- Support
- Contact information

Distinguish contextual links from generic navigation where possible.

### 4. Page-Level Next Actions

Determine which observable next-action signals are present on each crawled page.

Examples:

- Action-oriented link
- Contact pathway
- Product pathway
- Documentation pathway
- Related-content pathway
- No observable next-action signal

A lack of an observed signal must be reported conservatively.

It must not be treated as proof that the page contains no engagement mechanism.

### 5. Internal Link Coverage

Measure descriptive coverage of internal pathways across crawled pages.

Where possible, break coverage down by:

- Page type
- Destination page type
- Presence of action-oriented anchor text
- Internal-link count

Coverage is descriptive, not a quality score.

### 6. Link Quality Signals

Record observable characteristics that may affect interpretation:

- Empty anchor text
- Generic anchor text
- Repeated anchor text
- Absolute versus relative destination URLs
- Same-origin versus external destination
- Links to important page types
- Links whose destination was not observed in the crawl

Do not label these characteristics as harmful without additional evidence.

## Evidence Rules

Every observation must be traceable to the supplied evidence bundle.

Prefer:

- Source page URL
- Destination URL
- Exact anchor text
- Page type
- Link type
- Observed page metadata

Do not invent links, CTAs, destinations, or user intent.

Distinguish clearly between:

- Present
- Absent from observed evidence
- Not applicable
- Unable to determine

Absence of evidence is not proof that a website lacks an engagement mechanism.

## Output

Return a structured engagement-audit result containing:

- Skill name
- Schema version
- Summary statistics
- CTA observations
- Navigation observations
- Contextual-link observations
- Page-level engagement observations
- Coverage observations
- Limitations

Recommended structure:

```json
{
  "skill": "engagement-audit",
  "schema_version": "engagement-audit/v1",
  "summary": {},
  "observations": [],
  "coverage": {},
  "limitations": []
}