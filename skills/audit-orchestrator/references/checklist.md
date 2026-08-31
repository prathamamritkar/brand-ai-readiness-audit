# Release Checklist

## Structure
- [ ] `marketplace.json` with exactly one `entrypoint: true`
- [ ] All 4 skills have `SKILL.md` with YAML frontmatter
- [ ] `README.md` at root
- [ ] `scripts/audit_engine.py` uses only Python 3.9+ stdlib
- [ ] `references/` contains rubric, remediation, and checklist

## Function
- [ ] Runs without crash on arbitrary public URLs
- [ ] `--max-pages` is respected and actually crawls multiple pages
- [ ] Respects `robots.txt` and crawl-delay
- [ ] Handles 4xx/5xx, timeouts, SSL errors gracefully
- [ ] Completes in < 280 seconds
- [ ] Output JSON has `site`, `audited_at`, `summary`, `findings`
- [ ] Each finding has `id`, `title`, `severity`, `category`, `url`, `evidence`, `suggested_action`

## Generalization
- [ ] No hardcoded brands, prices, or slugs
- [ ] No CMS-specific assumptions
- [ ] Pattern-driven detection only
- [ ] Evidence derived from observed DOM/headers
