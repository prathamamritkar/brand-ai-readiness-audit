# Severity Rubric

| Severity | Trigger | Impact |
|----------|---------|--------|
| **critical** | `robots.txt` blocks AI bots; `noindex` meta or header on public pages; root domain unreachable. | Complete exclusion from AI indexes. |
| **high** | CSR wall (`< 150` words, `> 40KB` scripts); commerce text with zero `Product`/`Offer` schema; zero JSON-LD sitewide. | Retrieval failure; bi-encoders drop the page. |
| **medium** | Missing `BreadcrumbList`, `SpeakableSpecification`, `WebSite` (root), `sameAs`, `disambiguatingDescription`, `dateModified`, `Last-Modified`, canonical, deep anchors, referrer handling, flat taxonomy, sitemap `lastmod`, legacy 200s, Open Graph, semantic landmarks, heading issues. | Factual drift, hallucination, bounce, attribute conflation. |
