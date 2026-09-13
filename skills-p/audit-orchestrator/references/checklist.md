# Release Checklist

## Structure
- [ ] `marketplace.json` with exactly one `entrypoint: true`
- [ ] All 4 skills have `SKILL.md` with YAML frontmatter
- [ ] `README.md` at root
- [ ] `scripts/audit_engine.py` uses only Python 3.9+ stdlib + requests + bs4
- [ ] `references/` contains rubric, remediation, and checklist

## Function
- [ ] Runs without crash on arbitrary public URLs
- [ ] `--max-pages` is respected and actually crawls multiple pages
- [ ] Respects `robots.txt` and `Crawl-delay` (capped at 5 s per request)
- [ ] Handles 4xx/5xx, timeouts, SSL errors gracefully; records in `crawl_meta.errors`
- [ ] Handles malformed JSON-LD gracefully (parse error becomes a finding)
- [ ] Handles missing/malformed sitemap gracefully (distinct findings)
- [ ] Completes in < 300 seconds end-to-end (total audit runtime)
- [ ] Output JSON has `site`, `audited_at`, `crawl_meta`, `summary`, `findings`
- [ ] Each finding has `id`, `title`, `severity`, `gap_type`, `category`, `url`, `evidence`, `suggested_action`
- [ ] Each `suggested_action` has `summary`, `priority`, `scope`
- [ ] `gap_type` is one of: `indexing`, `citation`, `engagement`
- [ ] `scope` is one of: `page`, `site`, `brand`

## Generalization
- [ ] No hardcoded brands, prices, slugs, or CSS class names
- [ ] No CMS-specific assumptions
- [ ] Pattern-driven detection only
- [ ] Evidence derived from observed DOM/headers/schema
- [ ] Engagement checks only run on content pages (word_count > 200)
- [ ] sameAs/disambiguatingDescription checks only on Organization/Brand types
- [ ] Legacy URL probes are inferred from crawled URL patterns, not hardcoded
