import re
import logging
from typing import Optional

from serpapi import GoogleSearch

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Glassdoor-specific Google queries to find benefits reviews
QUERIES = [
    'site:glassdoor.com "Chicago" "learning stipend" OR "development budget" review',
    'site:glassdoor.com "Chicago" "tuition reimbursement" OR "education stipend" benefits',
    'site:glassdoor.com "Chicago" "professional development" "budget" OR "stipend" review',
    'site:glassdoor.com "Chicago" "training budget" OR "conference budget" employee',
    'site:glassdoor.com "Chicago" "L&D" OR "learning and development" benefits review',
    'site:glassdoor.com Chicago benefits "professional development" company review 2024 OR 2025',
    'site:glassdoor.com/Benefits Chicago "education" OR "learning" OR "development"',
]


def _extract_company_from_glassdoor_url(url: str) -> Optional[str]:
    """Extract company name from Glassdoor URL patterns."""
    patterns = [
        r"glassdoor\.com/Reviews/([^-]+?)(?:-Reviews|-Employee)",
        r"glassdoor\.com/Benefits/([^-]+?)(?:-Benefits|-US)",
        r"glassdoor\.com/Overview/Working-at-([^-]+?)(?:-EI_|\.htm)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            name = match.group(1).replace("-", " ").strip()
            if len(name) > 1:
                return name.title()
    return None


class GlassdoorScraper(BaseScraper):
    name = "glassdoor"
    rate_limit_seconds = 1.0

    def scrape(self) -> list[Company]:
        api_key = self.config.get("serpapi_key")
        if not api_key:
            self.logger.error("SERPAPI_KEY not set, skipping Glassdoor scraper")
            return []

        all_companies: dict[str, Company] = {}

        for query in QUERIES:
            self.logger.info(f"Searching Glassdoor: {query}")
            try:
                search = GoogleSearch({
                    "q": query,
                    "num": 20,
                    "api_key": api_key,
                })
                results = search.get_dict()
            except Exception as e:
                self.logger.error(f"SerpAPI error for Glassdoor query: {e}")
                continue

            organic = results.get("organic_results", [])
            for result in organic:
                link = result.get("link", "")
                snippet = result.get("snippet", "")
                title = result.get("title", "")

                company_name = _extract_company_from_glassdoor_url(link)
                if not company_name:
                    # Try extracting from title: "Company Name Reviews | Glassdoor"
                    title_match = re.match(r"^(.+?)\s+(?:Reviews|Benefits|Salaries)", title)
                    if title_match:
                        company_name = title_match.group(1).strip()
                        # Remove "Working at " prefix
                        company_name = re.sub(r"^Working at\s+", "", company_name)

                if not company_name or len(company_name) < 3:
                    continue

                # Filter junk: remove anything that looks like a snippet, not a company name
                junk_patterns = [
                    r"^\d+", r"^perk\b", r"^benefit\b", r"^review\b",
                    r"^salary\b", r"^job\b", r"^interview\b", r"^employee\b",
                ]
                if any(re.match(p, company_name.lower()) for p in junk_patterns):
                    continue
                if len(company_name) > 50:
                    continue
                # Reject names containing quotes or keywords that suggest snippet fragments
                if '"' in company_name or ":" in company_name:
                    continue
                noise_words = ["training", "tuition", "reimbursement", "benefit",
                               "budget", "stipend", "professional development",
                               "learning and development", "employee", "director of"]
                if any(nw in company_name.lower() for nw in noise_words):
                    continue

                key = company_name.lower().strip()
                evidence = f"Glassdoor: {snippet[:200]}" if snippet else f"Glassdoor: {title}"

                if key in all_companies:
                    existing = all_companies[key]
                    if evidence not in existing.lnd_evidence:
                        existing.lnd_evidence.append(evidence)
                    if link not in existing.lnd_source_urls:
                        existing.lnd_source_urls.append(link)
                else:
                    all_companies[key] = Company(
                        name=company_name,
                        has_lnd_budget=True,
                        lnd_evidence=[evidence],
                        lnd_source_urls=[link],
                        sources=["glassdoor"],
                        confidence_score=0.65,
                    )

            self._rate_limit()

        companies = list(all_companies.values())
        self.logger.info(f"Found {len(companies)} companies via Glassdoor")
        return companies
