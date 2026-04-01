# LnD Scraper — Claude Code Rules

## Project Overview
Chicago L&D Budget Company Scraper — finds Chicago companies offering Learning & Development budgets, enriches with HR contact info, and exports to CSV/Excel/JSON. Two web UIs: Flask (legacy) and Next.js (primary).

## Project Goals & Context
- **Purpose:** Generate a targeted lead list of mid-market Chicago companies (under 750 employees) that invest in L&D, along with HR/People Ops decision-maker contacts.
- **Target companies:** Traditional/non-tech industries in Chicago with active L&D budgets (tuition reimbursement, training stipends, learning platforms). Tech-native, AI, trading firms, and large enterprises are explicitly excluded.
- **Target contacts:** HR Directors, VP People, L&D Managers, Training Directors — anyone controlling L&D spend.
- **Cost strategy:** Maximize free sources first (DDG, career pages, email guesser), use paid APIs (SerpAPI, Apollo, Hunter) as supplements. Track credit usage strictly.
- **Quality bar:** Every data point must have source provenance and confidence scores. Prefer fewer high-quality leads over bulk low-quality data.
- **This is a batch pipeline**, not a live service. Run periodically to refresh the lead list. Results are consumed via the Next.js frontend or exported CSV/Excel.

## Architecture
- **Scrapers** (`scrapers/`): Each scraper extends `BaseScraper` from `base.py`. Sources: DDG Search (free), SerpAPI (Google + Jobs), Glassdoor, BuiltIn Chicago, Crain's, Great Place to Work, Career Pages (L&D confirmation).
- **Enrichment** (`enrichment/`): Apollo, Hunter, DDG LinkedIn finder, Google Search, Website Team pages, Domain Resolver, Email Guesser (pattern + SMTP).
- **Pipeline** (`main.py`): Scrape -> Deduplicate (fuzzy 85) -> Confirm L&D via career pages -> Resolve domains -> Filter (size ≤750, exclude tech/enterprises) -> Enrich contacts -> Export.
- **Models** (`models.py`): `Company`, `HRContact`, `EnrichedCompany` dataclasses with `to_dict()`/`from_dict()`.
- **Dedup** (`dedup.py`): Fuzzy matching with `thefuzz`, normalizes company names (strips Inc/LLC/Corp).
- **Export** (`export.py`): CSV (flat), Excel (two sheets), JSON (full provenance).
- **Flask UI** (`web/`): Browse results at localhost:5000.
- **Next.js Frontend** (`frontend/`): React 19 + Tailwind 4 + Next.js 16. Reads `data/final/results.json`. Has company detail pages, search, and CSV contact export API routes.
- **Config** (`config.py`): All API keys via `.env`, scraper/enrichment toggles, rate limits, filters.

## Key Files
- `main.py` — Pipeline orchestrator. Entry point for all modes (`--scrape-only`, `--enrich-only`, `--ui`).
- `config.py` — Central config dict. All API keys from `.env`. Scraper/enrichment enable/disable and rate limits.
- `models.py` — Three dataclasses: `Company`, `HRContact`, `EnrichedCompany`.
- `dedup.py` — Fuzzy deduplication. Threshold 85. Merges sources/evidence on match.
- `export.py` — CSV/Excel/JSON output to `data/final/`.
- `scrapers/base.py` — `BaseScraper` ABC. All scrapers inherit this.
- `scrapers/ddg_search.py` — Also contains `DDGContactFinder` used in enrichment.

## Coding Conventions
- Python 3.10+. Type hints on function signatures.
- Dataclasses for models, not dicts.
- Logging via `logging.getLogger("module_name")`. No print statements.
- All HTTP requests wrapped in try/except. Log and continue, never crash.
- Frontend: TypeScript, Next.js App Router, Tailwind CSS.

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

## New Scraper Checklist
1. Extend `BaseScraper` from `scrapers/base.py`
2. Implement `scrape()` returning `list[Company]`
3. Add config entry in `config.py` under `scrapers`
4. Register in `main.py:run_scrapers()`
5. Add rate limiting per config
6. Implement `save_raw()` for caching

## New Enrichment Source Checklist
1. Create module in `enrichment/`
2. Implement `search_hr_contacts(company_name, domain) -> list[HRContact]`
3. Add config entry in `config.py` under `enrichment`
4. Register in `main.py:run_enrichment()` with appropriate priority order
5. Track API credits if applicable
6. Return `HRContact` objects with `source` field set

## Testing
- Tests go in `tests/`. Use `pytest`.
- Mock HTTP calls in tests — never hit real APIs in CI.
- Test dedup logic with known edge cases (abbreviations, suffixes, typos).

## Exports
- CSV and Excel go to `data/final/`.
- JSON export includes full provenance (sources, confidence scores, evidence).
- Never export `.env` values or API keys in output files.

## Common Tasks

### Run the full pipeline
```bash
python main.py -v
```

### Run just scraping (Phase 1)
```bash
python main.py --scrape-only -v
```

### Run just enrichment (Phase 2, uses cached data)
```bash
python main.py --enrich-only -v
```

### Start Next.js frontend
```bash
cd frontend && npm run dev
```

### Start Flask UI
```bash
python main.py --ui
```

## Agent & Skill Guidelines

**IMPORTANT:** This project has access to 220+ global skills in `~/.claude-skills/` and 1,600+ skills via antigravity npm packages. USE THEM. Read `AGENTS.md` for the full mapping of which skills apply to which tasks.

### Mandatory skill usage triggers
- **Code review / PR review** → Read `~/.claude-skills/engineering-team/code-reviewer/` first
- **New scraper or enrichment module** → Read `~/.claude-skills/engineering-team/senior-backend/` for architecture, then follow the checklists above
- **Playwright / browser scraping** → Read `~/.claude-skills/engineering-team/playwright-pro/`
- **Security concern (API keys, data privacy)** → Read `~/.claude-skills/engineering-team/senior-security/`
- **Scraper broken by site change** → Read `~/.claude-skills/engineering-team/incident-response/`, use `/focused-fix`
- **Writing tests** → Use `/tdd` slash command
- **Analyzing lead quality or coverage** → Read `~/.claude-skills/product-team/` skills
- **Cost/ROI analysis of API usage** → Read `~/.claude-skills/finance/` skills
- **Frontend changes** → Read `~/.claude-skills/engineering-team/a11y-audit/` for accessibility

### Anti-patterns to avoid
- Don't scrape without rate limiting — this is a hard rule, not a suggestion.
- Don't store API keys anywhere except `.env`.
- Don't skip deduplication — all new data sources must go through `dedup.py`.
- Don't add contacts without the `source` field — provenance is required.
- Don't modify the `EXCLUDED_COMPANIES` set without explicit approval — it curates filtering of known large/tech companies.
- Don't ignore the global skills library — if a task matches a skill domain, read the skill file before executing.
