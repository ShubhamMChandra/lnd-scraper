# LnD Scraper — Claude Code Rules

## Project Overview
Chicago L&D Budget Company Scraper — finds Chicago companies offering Learning & Development budgets, enriches with HR contact info, and serves a local web UI.

## Architecture
- **Scrapers** (`scrapers/`): Each scraper extends `base.py`. Sources: SerpAPI (Google + Jobs), Glassdoor, BuiltIn Chicago, Crain's, Great Place to Work, career pages.
- **Enrichment** (`enrichment/`): Apollo, Hunter, Google Search, Website Team pages, Domain Resolver.
- **Pipeline**: Scrape -> Deduplicate -> Confirm L&D via career pages -> Resolve domains -> Enrich contacts -> Export (CSV/Excel/JSON).
- **Web UI** (`web/`): Flask app for browsing results.
- **Config**: All API keys via `.env`, scraper/enrichment toggles in `config.py`.

## Scraping & Web Utility Rules

### Rate Limiting & Politeness
- ALWAYS respect `rate_limit` config per scraper. Never remove or reduce delays.
- Add `time.sleep()` between requests. Default minimum: 1s for APIs, 3s for HTML scraping.
- Set a descriptive `User-Agent` header on all HTTP requests.
- Check and obey `robots.txt` before scraping new domains.

### Error Handling
- Wrap all HTTP requests in try/except. Log failures, never crash the pipeline.
- Use exponential backoff on 429/5xx responses (3 retries max).
- Always set timeouts on requests (default: 30s connect, 60s read).

### HTML Parsing
- Use `BeautifulSoup` with `lxml` parser for HTML.
- Use CSS selectors over XPath unless XPath is clearly simpler.
- Never rely on class names that look auto-generated (e.g., `css-1a2b3c`). Prefer semantic selectors.
- Validate extracted data — don't blindly trust page structure.

### API Integrations
- Track API credit/quota usage. Respect `max_credits` limits in config.
- Cache API responses in `data/raw/` to avoid redundant calls during development.
- Never hardcode API keys. Always use `CONFIG` from `config.py` -> `.env`.

### Data Quality
- Deduplicate using fuzzy matching (`dedup.py`, threshold: 85).
- Normalize company names (strip Inc/LLC/Corp suffixes) before comparison.
- Validate emails and domains before storing.
- Always preserve `sources` provenance — track where each data point came from.

### New Scraper Checklist
1. Extend `BaseScraper` from `scrapers/base.py`
2. Implement `scrape()` returning `list[Company]`
3. Add config entry in `config.py` under `scrapers`
4. Register in `main.py:run_scrapers()`
5. Add rate limiting per config
6. Implement `save_raw()` for caching

### Testing
- Tests go in `tests/`. Use `pytest`.
- Mock HTTP calls in tests — never hit real APIs in CI.
- Test dedup logic with known edge cases (abbreviations, suffixes, typos).

### Exports
- CSV and Excel go to `data/final/`.
- JSON export includes full provenance (sources, confidence scores, evidence).
- Never export `.env` values or API keys in output files.
