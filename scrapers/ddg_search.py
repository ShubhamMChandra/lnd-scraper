"""
DuckDuckGo-powered search scraper. FREE, no API key, no limits.
Replaces SerpAPI for company discovery and HR contact finding.
"""
import logging
import re
import time
from typing import Optional

from ddgs import DDGS

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Targeted queries for middle-market traditional Chicago companies with L&D
COMPANY_QUERIES = [
    # Industry-specific L&D queries
    'Chicago accounting firm "professional development" budget OR stipend',
    'Chicago law firm "learning and development" budget employee',
    'Chicago healthcare company "tuition reimbursement" OR "education stipend"',
    'Chicago manufacturing "training budget" OR "professional development"',
    'Chicago insurance company "learning and development" OR "education benefit"',
    'Chicago nonprofit "professional development" budget employee',
    'Chicago construction company "training budget" OR "tuition reimbursement"',
    'Chicago marketing agency "professional development" budget',
    'Chicago consulting firm "learning and development" stipend',
    'Chicago real estate company "professional development" OR "training budget"',
    'Chicago logistics company "tuition reimbursement" OR "education"',
    'Chicago financial services "professional development stipend"',
    'Chicago engineering firm "training budget" OR "professional development"',
    # General L&D queries
    '"Chicago" company "learning and development budget" employees',
    '"Chicago" employer "professional development stipend" benefit',
    '"Chicago" "we offer" "professional development" budget small business',
    'Chicago midsize company "education stipend" OR "learning stipend"',
    'Chicago company "annual training budget" per employee',
    # PDF benefit guides indexed by Google
    'filetype:pdf "Chicago" "learning and development" budget employee',
    'filetype:pdf "Chicago" "professional development stipend" benefits',
    # Best-of lists
    'best midsize companies Chicago professional development 2024 OR 2025',
    'best places work Chicago small company professional development',
    'Chicago "best places to work" small medium business 2025',
    # BuiltIn/Glassdoor site-specific
    'site:builtin.com Chicago "education stipend" small company',
    'site:glassdoor.com Chicago "training budget" OR "development budget" review',
]

COMPANY_NOISE = {
    "chicago", "glassdoor", "indeed", "linkedin", "builtin", "ziprecruiter",
    "google", "yelp", "facebook", "twitter", "wikipedia", "reddit",
    "we offer", "work", "budget", "stipend", "professional development",
    "learning and development", "training", "companies", "employer",
    "offer", "startups", "lmi", "home page", "page",
}

def _is_valid_ddg_company(name: str) -> bool:
    """Extra validation for DDG-extracted company names."""
    low = name.lower().strip()
    if low in COMPANY_NOISE:
        return False
    if len(low) < 3 or len(low) > 50:
        return False
    # Reject names with ellipsis, "..." or that look like snippets
    if "..." in name or "…" in name:
        return False
    # Reject names starting with common non-company words
    bad_starts = ["offer", "the best", "best ", "top ", "how ", "what ", "why ",
                  "list of", "companies that", "startups"]
    if any(low.startswith(b) for b in bad_starts):
        return False
    # Must contain at least one uppercase letter (proper noun)
    if not any(c.isupper() for c in name):
        return False
    return True


def _extract_companies_from_result(result: dict) -> list[dict]:
    """Extract company name hints from a search result."""
    companies = []
    title = result.get("title", "")
    body = result.get("body", "")
    href = result.get("href", "")

    # BuiltIn company URLs
    builtin_match = re.search(r"builtin\.com/company/([^/?#]+)", href)
    if builtin_match:
        name = builtin_match.group(1).replace("-", " ").title()
        if len(name) > 2:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    # Glassdoor URLs
    gd_match = re.search(r"glassdoor\.com/Reviews/([^-]+)-Reviews", href)
    if gd_match:
        name = gd_match.group(1).replace("-", " ").title()
        if len(name) > 2:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    # "at Company Name" pattern in titles
    at_match = re.search(r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[-|,]|\s+in\s+Chicago)", title)
    if at_match:
        name = at_match.group(1).strip()
        if (name.lower() not in COMPANY_NOISE and len(name) > 3
                and re.search(r"[A-Z]", name)):
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    return companies


class DDGSearchScraper(BaseScraper):
    """DuckDuckGo-powered company scraper. Free, unlimited."""
    name = "ddg_search"
    rate_limit_seconds = 2.0

    def scrape(self) -> list[Company]:
        ddgs = DDGS()
        all_companies: dict[str, Company] = {}

        for query in COMPANY_QUERIES:
            self.logger.info(f"DDG searching: {query[:60]}...")
            try:
                results = list(ddgs.text(query, max_results=10))
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"DDG error (skipping): {e}")
                time.sleep(3)
                continue

            for result in results:
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
                    elif _is_valid_ddg_company(name):
                        all_companies[key] = Company(
                            name=name,
                            has_lnd_budget=True,
                            lnd_evidence=[comp["evidence"]],
                            lnd_source_urls=[comp["url"]],
                            sources=["ddg_search"],
                            confidence_score=0.6,
                        )

        companies = list(all_companies.values())
        self.logger.info(f"Found {len(companies)} companies via DuckDuckGo")
        return companies


class DDGContactFinder:
    """Find HR contacts using DuckDuckGo. Free, unlimited."""

    def __init__(self):
        self.ddgs = DDGS()
        self.logger = logging.getLogger("enrichment.ddg_contacts")

    def find_hr_contacts(self, company_name: str, domain: Optional[str]) -> list[dict]:
        """Find HR/L&D contacts via DDG LinkedIn search."""
        query = f'"{company_name}" "HR" OR "People" OR "Talent" OR "Learning" director OR VP site:linkedin.com/in'

        try:
            results = list(self.ddgs.text(query, max_results=5))
            time.sleep(2)
        except Exception as e:
            self.logger.warning(f"DDG contact search error: {e}")
            return []

        contacts = []
        for result in results:
            link = result.get("href", "")
            title = result.get("title", "")

            if "linkedin.com/in/" not in link:
                continue

            # Parse "First Last - Title - Company | LinkedIn"
            name_match = re.match(r"^(.+?)\s*[-–—|]", title)
            if not name_match:
                continue

            full_name = name_match.group(1).strip()
            parts = full_name.split()
            if len(parts) < 2:
                continue

            # Extract title
            person_title = ""
            title_match = re.search(r"[-–—]\s*(.+?)\s*[-–—]", title)
            if title_match:
                person_title = title_match.group(1).strip()

            # Verify HR-related
            combined = f"{person_title} {result.get('body', '')}".lower()
            hr_keywords = ["hr", "human resource", "people", "talent",
                           "learning", "development", "recruit", "training"]
            if not any(kw in combined for kw in hr_keywords):
                continue

            contacts.append({
                "first_name": parts[0],
                "last_name": " ".join(parts[1:]),
                "full_name": full_name,
                "title": person_title,
                "linkedin_url": link,
            })

        return contacts
