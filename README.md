# Chicago L&D Company Scraper

Automated pipeline that discovers Chicago-area companies offering Learning & Development budgets, enriches them with HR contact information, and serves results through a web UI.

## Project Goals

**Primary goal:** Build a targeted lead list of mid-market Chicago companies that invest in employee learning and development — specifically to identify HR/People Ops decision-makers who control L&D budgets.

### Target Company Profile
- **Location:** Chicago metro area
- **Size:** Small to mid-market (under 750 employees)
- **Industry:** Traditional/non-tech industries (manufacturing, healthcare, finance, professional services, etc.) — tech-native and AI companies are excluded since they're already saturated
- **Key signal:** Active L&D budget or professional development benefits (tuition reimbursement, training stipends, conference budgets, learning platforms)

### Target Contact Profile
- HR Directors, VP of People, Chief People Officer
- L&D Managers, Training Directors
- Talent Development leads
- Anyone with "Learning", "Development", "Training", or "People" in their title

### Success Metrics
- **Coverage:** Identify 50+ confirmed L&D companies in Chicago
- **Contact quality:** Email addresses for 60%+ of discovered contacts
- **Provenance:** Every data point traced to its source with confidence scores
- **Cost efficiency:** Maximize free sources (DDG, career pages, email guessing) before burning paid API credits

### What This Is NOT
- Not a mass cold-email tool — this generates targeted research for personalized outreach
- Not a real-time service — it's a batch pipeline you run periodically to refresh data
- Not limited to one data source — the multi-source approach with dedup catches companies that any single source would miss

## What It Does

1. **Scrapes** multiple sources to find companies with L&D / professional development benefits
2. **Deduplicates** results using fuzzy name matching (threshold: 85)
3. **Confirms** L&D budgets by scanning career pages for evidence
4. **Filters** out tech-native companies and large enterprises (750+ employees)
5. **Enriches** with HR/People contacts (names, titles, emails, LinkedIn)
6. **Exports** to CSV, Excel, and JSON

## Data Sources

### Scrapers
| Source | Method | API Key Required |
|---|---|---|
| DuckDuckGo Search | HTML scraping | No (free) |
| SerpAPI Google | API | Yes (`SERPAPI_KEY`) |
| SerpAPI Jobs | API | Yes (`SERPAPI_KEY`) |
| Glassdoor | API via SerpAPI | Yes (`SERPAPI_KEY`) |
| BuiltIn Chicago | HTML scraping | No |
| Crain's Chicago | HTML scraping | No |
| Great Place to Work | HTML scraping | No |
| Career Pages | HTML scraping | No (confirmation step) |

### Enrichment
| Source | What It Provides | API Key Required |
|---|---|---|
| Hunter.io | Verified emails, domain search | Yes (`HUNTER_API_KEY`) |
| Apollo.io | Contact names, titles, emails | Yes (`APOLLO_API_KEY`) |
| DuckDuckGo | LinkedIn profile URLs | No (free) |
| Google Search | Contact discovery via SerpAPI | Yes (`SERPAPI_KEY`) |
| Website Team Pages | Names/titles from /about, /team | No |
| Email Guesser | Pattern-based email + SMTP verify | No |

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for Next.js frontend)

### Installation

```bash
# Clone and install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (for JS-rendered pages)
playwright install chromium

# Copy env file and add your API keys
cp .env.example .env
```

### Environment Variables

```
SERPAPI_KEY=       # serpapi.com — Google/Jobs/Glassdoor searches
APOLLO_API_KEY=   # apollo.io — contact enrichment
HUNTER_API_KEY=   # hunter.io — email finder/verifier
```

All API keys are optional. The pipeline works without them using free scrapers (DDG, BuiltIn, career pages) and the email guesser, but results will be more limited.

## Usage

### Full Pipeline
```bash
# Run everything: scrape -> enrich -> export
python main.py

# With verbose logging
python main.py -v

# Limit to N companies
python main.py --limit 20
```

### Phased Execution
```bash
# Phase 1 only: scrape and save to data/raw/
python main.py --scrape-only

# Phase 2 only: enrich cached scrape results
python main.py --enrich-only
```

### Web UI (Flask)
```bash
python main.py --ui
# Opens at http://localhost:5000
```

### Next.js Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

The Next.js frontend reads from `data/final/results.json` and provides company browsing, search, and CSV contact export.

## Output

Results are saved to `data/final/`:
- `chicago_lnd_companies_YYYYMMDD.csv` — flat CSV with one row per contact
- `chicago_lnd_companies_YYYYMMDD.xlsx` — Excel with company + contact sheets
- `results.json` — full structured data with provenance and confidence scores

## Project Structure

```
├── main.py              # Pipeline orchestrator (scrape/enrich/export/UI)
├── config.py            # Configuration and API key loading
├── models.py            # Data models (Company, HRContact, EnrichedCompany)
├── dedup.py             # Fuzzy deduplication logic
├── export.py            # CSV/Excel/JSON exporters
├── scrapers/
│   ├── base.py          # BaseScraper abstract class
│   ├── serpapi_google.py
│   ├── serpapi_jobs.py
│   ├── glassdoor.py
│   ├── builtin_chicago.py
│   ├── crains.py
│   ├── greatplacetowork.py
│   ├── ddg_search.py
│   └── career_pages.py  # L&D confirmation via career pages
├── enrichment/
│   ├── apollo.py        # Apollo.io contact enrichment
│   ├── hunter.py        # Hunter.io email finder
│   ├── google_search.py # SerpAPI Google contact search
│   ├── website_team.py  # Scrape /about and /team pages
│   ├── domain_resolver.py
│   └── email_guesser.py # Pattern guess + SMTP verification
├── web/                 # Flask web UI
│   ├── app.py
│   ├── templates/
│   └── static/
├── frontend/            # Next.js frontend (React 19, Tailwind 4)
├── data/
│   ├── raw/             # Cached scraper outputs (JSON)
│   └── final/           # Exported results (CSV, Excel, JSON)
└── tests/
```

## Configuration

All scraper/enrichment toggles and rate limits are in `config.py`. Key settings:

- **Rate limits**: Per-scraper delays (1-3s) to be polite to target sites
- **API credit caps**: `max_credits` per enrichment source to control spend
- **Filters**: `max_employees: 750`, excludes tech/AI-native companies and known large enterprises
- **Dedup threshold**: Fuzzy match score of 85 for company name deduplication

## License

Private project. Not for redistribution.
