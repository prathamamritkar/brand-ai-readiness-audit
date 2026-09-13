# Severity Rubric

| Severity | Gap Type | Trigger | Impact |
|----------|----------|---------|--------|
| **critical** | indexing | `robots.txt` blocks AI bots; `noindex` meta or `X-Robots-Tag` on public pages. | Complete exclusion from AI source pool. Brand absent from all AI answers. |
| **high** | indexing | CSR rendering barrier (< 150 words, > 40 KB scripts + framework markers); missing `<title>` tag. | Crawler reaches URL but cannot extract content. |
| **high** | citation | Commerce text without `Product`/`Offer` schema; zero JSON-LD sitewide; both OG tags absent. | AI extractor skips page or cites it without brand-critical facts. |
| **medium** | indexing | Missing or drifted `rel=canonical`; sitemap absent or malformed. | Duplicate indexing risk; authority dilution. |
| **medium** | citation | Missing `BreadcrumbList`, `sameAs`, `disambiguatingDescription`, `dateModified`, meta description, stale date on commerce page, `llms.txt` absent or malformed, missing `Last-Modified`, legacy URLs returning 200, Open Graph incomplete, semantic landmarks absent, heading issues, `SpeakableSpecification` absent (proactive). | Factual drift, hallucination risk, entity conflation. |
| **medium** | engagement | Sparse section anchors, no referrer-awareness pattern, CTA below fold or absent, `noscript` content divergence, cross-category semantic bleed. | High bounce from AI referrals; visitor loses context on arrival. |
