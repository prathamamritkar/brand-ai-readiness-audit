# Release Checklist

## Structure
- [ ] `marketplace.json` with exactly one `entrypoint: true`
- [ ] All 5 skills have `SKILL.md` with YAML frontmatter
- [ ] `README.md` at root
- [ ] `scripts/audit_engine.py` executable with Python 3.9+ standard library (zero external dependencies)
- [ ] `references/` contains rubric, remediation, and checklist

## Function
- [ ] Runs without crash on arbitrary public URLs
- [ ] `--max-pages` is respected and crawls internal pages
- [ ] Respects `robots.txt` and `Crawl-delay` (capped at 5 s per request)
- [ ] Handles 4xx/5xx, timeouts, SSL errors gracefully; records in `crawl_meta.errors`
- [ ] Handles malformed JSON-LD gracefully (parse error becomes a finding)
- [ ] Handles missing/malformed sitemap gracefully (distinct findings)
- [ ] Completes in < 280 seconds end-to-end (total audit runtime ceiling)
- [ ] Output JSON has `site`, `audited_at`, `crawl_meta`, `summary`, `findings`
- [ ] Each finding has `id`, `title`, `severity`, `gap_type`, `category`, `url`, `evidence`, `suggested_action`
- [ ] Each `suggested_action` has `summary`, `priority`, `scope`
- [ ] `summary` includes `ai_readiness_score` (0–100), `headline`, `top_priority`, and `phase_verdicts`

## Generalization
- [ ] No hardcoded brands, prices, slugs, or CSS class names
- [ ] No CMS-specific assumptions
- [ ] Pattern-driven detection only
- [ ] Evidence derived from observed DOM/headers/schema
- [ ] Engagement checks only run on content pages (word_count > 200)
- [ ] sameAs/disambiguatingDescription checks run on Organization/Brand types
- [ ] Legacy URL probes are inferred from crawled URL patterns, not hardcoded
