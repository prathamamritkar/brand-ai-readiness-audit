# Site Evidence Bundle v0.1

The site-intelligence skill produces one JSON document with four top-level areas:

- `schema_version`: identifies the evidence contract version.
- `site`: normalized input URL and origin.
- `crawl`: bounded crawl configuration and runtime observations.
- `robots` / `sitemap`: discovery and access observations.
- `pages`: page-level fetch and extraction evidence.

## Principle

This bundle records observations. It does not infer severity, confidence, root cause, or recommendations.

Downstream skills must treat missing evidence as unknown rather than as proof of absence unless the collection step explicitly establishes absence.
