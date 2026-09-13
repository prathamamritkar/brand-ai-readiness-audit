# Remediation Catalog

## 1. robots.txt
```
User-agent: GPTBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: PerplexityBot
Allow: /
Sitemap: https://example.com/sitemap.xml
```

## 2. Indexing Hygiene
Remove `noindex` / `X-Robots-Tag: noindex` from all public pages.

## 3. CSR Fix
Implement SSR or dynamic rendering for AI user-agents. Verify: `curl -s URL | wc -w` > 200.

## 4. Semantic HTML
```html
<main>
  <article>
    <h1>Product Name</h1>
    <section id="specifications">...</section>
    <section id="pricing">...</section>
  </article>
</main>
```

## 5. Schema.org Stack
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "WebSite", "url": "https://example.com"},
    {"@type": "Organization", "name": "Brand", "sameAs": ["https://www.wikidata.org/..."], "disambiguatingDescription": "..."},
    {"@type": "Product", "name": "Item", "category": "Running Shoes", "offers": {"@type": "Offer", "price": "99", "priceCurrency": "USD"}},
    {"@type": "BreadcrumbList", "itemListElement": [...]},
    {"@type": "SpeakableSpecification", "cssSelector": [".speakable"]}
  ]
}
```

## 6. /llms.txt
```markdown
# Brand Name
## Products
- [Item](https://example.com/item): Category, price, specs.
```

## 7. Temporal Signals
- `dateModified` in JSON-LD.
- `Last-Modified` HTTP header.
- `<lastmod>` in sitemap.xml.

## 8. Legacy Tombstoning
```nginx
location /old-item { return 410; }
rewrite ^/legacy$ /new permanent;
```

## 9. Edge Intent Bridge
```javascript
// Cloudflare Worker
const referrer = request.headers.get('Referer') || '';
if (/chatgpt|perplexity|claude/.test(referrer)) {
  headers.set('X-AI-Intent-Bridge', 'active');
}
```

## 10. Taxonomy Isolation
```
/performance/running/shoe-x9
/lifestyle/ethnic/heritage-pro
```
