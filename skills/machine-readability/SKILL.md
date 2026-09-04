---
name: machine-readability
description: Analyze structured and semantic website signals that help AI agents and other machines understand pages, entities, content relationships, and brand information. Use this skill when evaluating machine-readable representation and discoverability of a public website.
---

# Machine Readability

## Purpose

Analyze machine-readable and semantic signals in a website's evidence bundle.

This skill determines what structured information is available to machines and how well it represents the visible website content.

This skill is observation-focused. It must not assign overall website visibility scores, diagnose final root causes, or prescribe fixes.

## Input

Consume the Site Intelligence Evidence Bundle.

Expected input:

- Site metadata
- Crawl metadata
- Page records
- Page URLs and types
- Titles and meta descriptions
- Canonical URLs
- Headings
- Visible text
- JSON-LD blocks
- Link information
- Robots and sitemap observations

Do not crawl the website independently when the required evidence is already present in the bundle.

## Analysis Areas

### 1. Structured Data

Inspect available JSON-LD and identify:

- Schema.org types
- Number of structured-data blocks
- Entity identifiers such as `@id`
- URLs
- `sameAs`
- Relationships between entities
- Nested entities
- Important properties that are present or absent

Do not assume a single schema type is appropriate for every website.

### 2. Entity Representation

Identify machine-readable representations of entities such as:

- Organization
- Person
- Product
- Service
- Article
- WebSite
- WebPage
- LocalBusiness
- Other Schema.org entities

Report what is actually observed.

Do not mark an entity as missing solely because it is not expected for a particular industry.

### 3. Page Identity

Inspect:

- Page title
- Meta description
- Canonical URL
- Headings
- Page type
- URL structure
- Language information when available

Identify whether the page contains clear machine-readable identity signals.

### 4. Content and Structured Data Consistency

Compare available structured data with visible page evidence.

Examples:

- Product name in structured data versus visible product name
- Organization name versus visible brand name
- Article information versus page content
- URL in structured data versus canonical/page URL

Only report inconsistencies when there is sufficient evidence.

### 5. Entity Relationships

Inspect relationships expressed through:

- `@id`
- `url`
- `sameAs`
- `mainEntity`
- `mainEntityOfPage`
- `about`
- `isPartOf`
- `publisher`
- Other explicit structured relationships

Record observed relationships without inferring unsupported ones.

### 6. Coverage

Measure which crawled pages contain useful machine-readable signals.

Break coverage down where possible by:

- Page type
- Structured-data presence
- Entity type

Coverage is descriptive, not a quality score.

## Evidence Rules

Every observation must be traceable to evidence from the input bundle.

Prefer:

- Exact URL
- Observed schema type
- Observed property
- Extracted value
- Source page
- Relevant page metadata

Do not invent structured data or infer properties that were not observed.

Distinguish clearly between:

- Present
- Absent from observed evidence
- Not applicable
- Unable to determine

Absence of evidence is not proof that a website lacks the feature.

## Output

Return a structured machine-readability result containing:

- Skill name
- Schema version
- Summary statistics
- Structured-data observations
- Entity observations
- Page identity observations
- Consistency observations
- Relationship observations
- Coverage observations
- Limitations

Recommended structure:

```json
{
  "skill": "machine-readability",
  "schema_version": "machine-readability/v1",
  "summary": {},
  "observations": [],
  "coverage": {},
  "limitations": []
}