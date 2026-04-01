# LnD Scraper — Agent & Skills Guide

## Project Agents

### Scraper Agent
**When to use:** Adding new data sources, fixing broken scrapers, expanding search queries.
**Context needed:** Read `scrapers/base.py` for the `BaseScraper` interface, check `config.py` for the scraper config structure, and review an existing scraper (e.g., `scrapers/ddg_search.py`) as a reference implementation.
**Rules:**
- Always extend `BaseScraper`
- Always implement `scrape()` -> `list[Company]` and `save_raw()`
- Always add rate limiting from config
- Register in `main.py:run_scrapers()`
- Cache raw responses to `data/raw/`

### Enrichment Agent
**When to use:** Adding new contact enrichment sources, improving email discovery, expanding contact coverage.
**Context needed:** Read `enrichment/` modules for patterns, check `models.py` for `HRContact` structure, review the enrichment waterfall in `main.py:run_enrichment()`.
**Rules:**
- Return `list[HRContact]` with `source` field always set
- Track API credit usage against `max_credits`
- Fit into the waterfall priority order in `run_enrichment()`
- Free sources should run before paid sources

### Data Quality Agent
**When to use:** Improving dedup accuracy, validating scraped data, cleaning up results, analyzing coverage gaps.
**Context needed:** Read `dedup.py` for fuzzy matching logic, `models.py` for data structures, `data/final/results.json` for current output.
**Rules:**
- Fuzzy threshold is 85 — changes need justification
- Company name normalization strips Inc/LLC/Corp
- Every data point needs source provenance
- Confidence scores range 0.0-1.0

### Frontend Agent
**When to use:** Modifying the Next.js frontend, adding new views, updating the API routes.
**Context needed:** Read `frontend/AGENTS.md` for Next.js-specific rules, `frontend/lib/types.ts` for data types, `frontend/app/` for page structure.
**Rules:**
- TypeScript only, no `any` types
- App Router (not Pages Router)
- Data comes from `data/final/results.json` via API routes
- Tailwind CSS 4 for styling

### Pipeline Agent
**When to use:** Modifying the end-to-end pipeline flow, changing filter logic, adjusting the scrape->enrich->export sequence.
**Context needed:** Read `main.py` top to bottom — it's the orchestrator. Check `config.py` for all toggles. Review `EXCLUDED_COMPANIES` set before modifying filters.
**Rules:**
- Don't modify `EXCLUDED_COMPANIES` without explicit approval
- Filter order matters: size filter before tech filter
- `--scrape-only` and `--enrich-only` must remain independent
- Never skip deduplication

## Global Skills Library (Antigravity + Claude Skills)

These are installed globally and SHOULD be used proactively when tasks match. Read the relevant skill file before executing the task.

### Engineering Skills (`~/.claude-skills/engineering-team/`)
| Skill | When to use in this project |
|---|---|
| `code-reviewer` | Reviewing any PR or code change — scrapers, enrichment, pipeline |
| `senior-backend` | Python architecture decisions, pipeline refactoring, data model changes |
| `senior-security` | Reviewing API key handling, `.env` safety, data privacy, scraping ethics |
| `cloud-security` | If deploying the pipeline or frontend to cloud |
| `incident-response` | When a scraper breaks due to site changes or API issues |
| `playwright-pro` | Writing or debugging Playwright-based scrapers (career pages, JS-rendered sites) |
| `a11y-audit` | Accessibility review of the Next.js frontend |

### Advanced Engineering Skills (`~/.claude-skills/engineering/`)
36 POWERFUL-tier skills for CI/CD, database, observability, RAG, MCP, etc. Use when:
- Setting up CI/CD for the scraper pipeline
- Adding database storage instead of JSON files
- Building observability/monitoring for scraper health

### Agent Skills (`~/.claude-skills/agents/`)
Pre-built agent personas across domains. Use `engineering-team` agent for scraper dev, `product` agent for analyzing lead quality, `business-growth` agent for evaluating L&D market strategy.

### Product Skills (`~/.claude-skills/product-team/`)
| Skill | When to use |
|---|---|
| RICE prioritization | Prioritizing which scrapers/sources to build next |
| User stories | Writing requirements for new scraper features |
| UX research | Improving the frontend browsing experience |

### Business & Growth Skills (`~/.claude-skills/business-growth/`)
Use for analyzing the L&D market opportunity, evaluating lead list ROI, planning outreach strategy.

### Marketing Skills (`~/.claude-skills/marketing-skill/`)
Use if building email outreach templates or messaging for the contacts discovered.

### Finance Skills (`~/.claude-skills/finance/`)
Use for API cost analysis — tracking SerpAPI/Apollo/Hunter spend vs lead yield.

### Global npm Packages
| Package | When to use |
|---|---|
| `antigravity-awesome-skills` | Browse 1,300+ skills when no built-in skill fits |
| `antigravity-ide` | Fractal Memory System for long-running tasks |
| `antigravity-usage` | Check Claude model quota before long pipeline runs |
| `@rmyndharis/antigravity-skills` | 300+ specialized skills — search when core skills don't cover it |
| `claude-flow` | Multi-agent orchestration if parallelizing scrapers |
| `skills` (Vercel) | Universal agent skills CLI |
| `agent-skills-cli` | Install additional skills into this project |

## Slash Commands Useful for This Project
- `/tdd` — Generate tests for new scrapers or enrichment modules
- `/focused-fix` — Deep-dive repair when a scraper breaks due to site changes
- `/tech-debt` — Scan for scraping anti-patterns, missing error handling
- `/code-to-prd` — Reverse-engineer the frontend into requirements
- `/pipeline` — Generate CI/CD config for automating the scrape pipeline
- `/sprint-plan` — Plan sprints around scraper/enrichment development
- `/competitive-matrix` — Compare data sources by coverage, cost, reliability
