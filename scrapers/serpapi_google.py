import re
import logging

from serpapi import GoogleSearch

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

QUERIES = [
    '"Chicago" "learning and development budget" company',
    '"Chicago" "professional development stipend" employer',
    '"Chicago" "tuition reimbursement" "best companies"',
    '"Chicago" "L&D budget" employees',
    '"Chicago" "training budget" per employee company',
    '"Chicago" company "professional development" budget 2025',
    '"Chicago" employer "education stipend" OR "learning stipend"',
    '"Chicago" "we offer" "professional development" budget',
    '"Chicago" "$" "learning" "per year" stipend employee',
    'best companies Chicago professional development benefits 2025',
    'Chicago startups learning development stipend employee benefits',
    'Chicago tech companies education reimbursement benefits',
    '"Chicago" "career development fund" OR "skill development budget"',
    '"Chicago" "conference budget" OR "training allowance" company',
    'site:builtin.com Chicago "education stipend" OR "tuition reimbursement"',
    '"Chicago office" "learning and development" benefits company',
    'Chicago IL companies "professional development budget" employee perks',
    '"Chicago" "annual learning" OR "annual education" stipend company',
]

# Common patterns that indicate a company name in search results
COMPANY_NOISE = {
    "chicago", "glassdoor", "indeed", "linkedin", "builtin", "ziprecruiter",
    "salary", "review", "jobs", "careers", "benefits", "google", "yelp",
    "facebook", "twitter", "wikipedia", "reddit", "we offer", "work",
    "the best", "best companies", "top companies", "company", "employer",
    "employee", "budget", "stipend", "tandem", "ripple", "replicated",
    "professional development", "learning and development", "training",
    "tuition", "education", "reimbursement", "annual", "companies",
}


def _extract_companies_from_result(result: dict) -> list[dict]:
    """Extract company name hints from a single search result."""
    companies = []
    title = result.get("title", "")
    snippet = result.get("snippet", "")
    link = result.get("link", "")

    # Try to extract from builtin.com company URLs
    builtin_match = re.search(r"builtin\.com/company/([^/?#]+)", link)
    if builtin_match:
        name = builtin_match.group(1).replace("-", " ").title()
        companies.append({"name": name, "url": link, "evidence": snippet})

    # Try to extract from glassdoor URLs
    gd_match = re.search(r"glassdoor\.com/Reviews/([^-]+)-Reviews", link)
    if gd_match:
        name = gd_match.group(1).replace("-", " ").title()
        companies.append({"name": name, "url": link, "evidence": snippet})

    # Look for company names in title patterns like "Company Name - Benefits" or "at Company Name"
    at_match = re.search(r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[-|,]|\s+in\s+Chicago)", title)
    if at_match:
        name = at_match.group(1).strip()
        if name.lower() not in COMPANY_NOISE and len(name) > 2:
            companies.append({"name": name, "url": link, "evidence": snippet})

    return companies


class SerpAPIGoogleScraper(BaseScraper):
    name = "serpapi_google"
    rate_limit_seconds = 1.0

    def scrape(self) -> list[Company]:
        api_key = self.config.get("serpapi_key")
        if not api_key:
            self.logger.error("SERPAPI_KEY not set, skipping Google search scraper")
            return []

        all_companies: dict[str, Company] = {}

        for query in QUERIES:
            self.logger.info(f"Searching: {query}")
            try:
                search = GoogleSearch({
                    "q": query,
                    "location": "Chicago, Illinois, United States",
                    "num": 20,
                    "api_key": api_key,
                })
                results = search.get_dict()
            except Exception as e:
                self.logger.error(f"SerpAPI error for query '{query}': {e}")
                continue

            organic = results.get("organic_results", [])
            for result in organic:
                extracted = _extract_companies_from_result(result)
                for comp in extracted:
                    name = comp["name"]
                    key = name.lower().strip()
                    if key in all_companies:
                        existing = all_companies[key]
                        if comp["evidence"] not in existing.lnd_evidence:
                            existing.lnd_evidence.append(comp["evidence"])
                        if comp["url"] not in existing.lnd_source_urls:
                            existing.lnd_source_urls.append(comp["url"])
                    else:
                        all_companies[key] = Company(
                            name=name,
                            has_lnd_budget=True,
                            lnd_evidence=[comp["evidence"]],
                            lnd_source_urls=[comp["url"]],
                            sources=["serpapi_google"],
                            confidence_score=0.6,
                        )

            self._rate_limit()

        companies = list(all_companies.values())
        self.logger.info(f"Found {len(companies)} companies via Google search")
        return companies
