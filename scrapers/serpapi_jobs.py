import logging

from serpapi import GoogleSearch

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

JOB_QUERIES = [
    "learning and development budget Chicago",
    "professional development stipend Chicago",
    "tuition reimbursement Chicago",
    "training budget employee Chicago",
    "education stipend Chicago",
]


class SerpAPIJobsScraper(BaseScraper):
    name = "serpapi_jobs"
    rate_limit_seconds = 1.0

    def scrape(self) -> list[Company]:
        api_key = self.config.get("serpapi_key")
        if not api_key:
            self.logger.error("SERPAPI_KEY not set, skipping Jobs scraper")
            return []

        all_companies: dict[str, Company] = {}

        for query in JOB_QUERIES:
            self.logger.info(f"Searching jobs: {query}")
            try:
                search = GoogleSearch({
                    "engine": "google_jobs",
                    "q": query,
                    "location": "Chicago, Illinois, United States",
                    "api_key": api_key,
                })
                results = search.get_dict()
            except Exception as e:
                self.logger.error(f"SerpAPI jobs error for '{query}': {e}")
                continue

            jobs = results.get("jobs_results", [])
            for job in jobs:
                company_name = job.get("company_name", "").strip()
                if not company_name or len(company_name) < 3 or len(company_name) > 60:
                    continue
                # Filter junk names
                if any(x in company_name.lower() for x in ['"', ":", "employee", "director", "manager"]):
                    continue

                key = company_name.lower()
                description = job.get("description", "")
                title = job.get("title", "")
                evidence = f"Job posting: {title}"

                # Look for specific dollar amounts or L&D mentions in description
                desc_lower = description.lower()
                lnd_keywords = [
                    "learning and development", "professional development",
                    "education stipend", "tuition reimbursement", "training budget",
                    "learning budget", "development fund", "conference budget",
                    "l&d", "continuing education", "career development",
                    "learning stipend", "skill development",
                ]
                has_lnd = any(kw in desc_lower for kw in lnd_keywords)

                if key in all_companies:
                    existing = all_companies[key]
                    if evidence not in existing.lnd_evidence:
                        existing.lnd_evidence.append(evidence)
                    if has_lnd:
                        existing.has_lnd_budget = True
                        existing.confidence_score = max(existing.confidence_score, 0.7)
                else:
                    all_companies[key] = Company(
                        name=company_name,
                        has_lnd_budget=has_lnd,
                        lnd_evidence=[evidence],
                        sources=["serpapi_jobs"],
                        confidence_score=0.7 if has_lnd else 0.3,
                    )

            self._rate_limit()

        companies = list(all_companies.values())
        self.logger.info(f"Found {len(companies)} companies via job search")
        return companies
