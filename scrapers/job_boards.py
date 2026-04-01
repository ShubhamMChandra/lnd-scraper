"""
Job Board scraper via DuckDuckGo. Searches Indeed, ZipRecruiter, and Monster
for Chicago job postings that mention L&D benefits (tuition reimbursement,
professional development budgets, training stipends, etc.).

ICP: middle-market (50-750 employees), traditional industries in Chicago.
Explicitly excludes tech/AI/SaaS companies.
"""
import logging
import re
import time

from ddgs import DDGS

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Target industries (middle-market, traditional, Chicago)
# ---------------------------------------------------------------------------
INDUSTRIES = [
    "healthcare",
    "manufacturing",
    "financial services",
    "accounting",
    "law firm",
    "real estate",
    "construction",
    "logistics",
    "nonprofit",
    "insurance",
    "engineering",
]

# ---------------------------------------------------------------------------
# ~30 targeted queries across job board sites
# ---------------------------------------------------------------------------
JOB_BOARD_QUERIES = [
    # -- site:indeed.com  tuition reimbursement + industry --------------------
    'site:indeed.com Chicago "tuition reimbursement" healthcare',
    'site:indeed.com Chicago "tuition reimbursement" manufacturing',
    'site:indeed.com Chicago "tuition reimbursement" "financial services"',
    'site:indeed.com Chicago "tuition reimbursement" accounting',
    'site:indeed.com Chicago "tuition reimbursement" "law firm"',
    'site:indeed.com Chicago "tuition reimbursement" "real estate"',
    'site:indeed.com Chicago "tuition reimbursement" construction',
    'site:indeed.com Chicago "tuition reimbursement" logistics',
    'site:indeed.com Chicago "tuition reimbursement" nonprofit',

    # -- site:indeed.com  professional development + industry -----------------
    'site:indeed.com Chicago "professional development" budget healthcare',
    'site:indeed.com Chicago "professional development" budget manufacturing',
    'site:indeed.com Chicago "professional development" stipend accounting',
    'site:indeed.com Chicago "professional development" stipend insurance',
    'site:indeed.com Chicago "professional development" "law firm"',
    'site:indeed.com Chicago "professional development" "real estate"',
    'site:indeed.com Chicago "professional development" construction',

    # -- site:ziprecruiter.com  training budget + misc industries -------------
    'site:ziprecruiter.com Chicago "training budget" healthcare',
    'site:ziprecruiter.com Chicago "training budget" manufacturing',
    'site:ziprecruiter.com Chicago "training budget" "financial services"',
    'site:ziprecruiter.com Chicago "training budget" accounting OR insurance',
    'site:ziprecruiter.com Chicago "tuition reimbursement" construction OR logistics',
    'site:ziprecruiter.com Chicago "professional development" nonprofit',

    # -- General indeed/ziprecruiter L&D benefits ----------------------------
    'site:indeed.com Chicago "learning and development" budget -software -saas',
    'site:indeed.com Chicago "education stipend" OR "learning stipend" -tech',
    'site:ziprecruiter.com Chicago "education reimbursement" OR "training stipend"',

    # -- site:monster.com  broad queries -------------------------------------
    'site:monster.com Chicago "tuition reimbursement" OR "training budget"',
    'site:monster.com Chicago "professional development" healthcare OR manufacturing',

    # -- "hiring" + L&D keywords + Chicago + industry (cross-board) ----------
    'hiring Chicago "tuition reimbursement" healthcare -software -saas -startup',
    'hiring Chicago "professional development budget" manufacturing OR construction',
    'hiring Chicago "training budget" "financial services" OR accounting OR insurance',
]

# ---------------------------------------------------------------------------
# Noise words and tech company markers
# ---------------------------------------------------------------------------
COMPANY_NOISE = {
    "chicago", "indeed", "ziprecruiter", "monster", "linkedin", "glassdoor",
    "google", "yelp", "facebook", "twitter", "wikipedia", "reddit",
    "job search", "job posting", "apply now", "sign in", "log in",
    "professional development", "tuition reimbursement", "training budget",
    "learning and development", "education stipend", "hiring",
    "companies", "employer", "offer", "page", "home page", "salary",
    "jobs", "careers", "career", "benefits", "job", "we offer",
}

TECH_MARKERS = {
    "saas", "software", "ai ", " ai", "machine learning", "fintech",
    "edtech", "medtech", "startup", "app ", "platform", "cloud",
    "devops", "blockchain", "crypto", "nft",
}


def _is_valid_company(name: str) -> bool:
    """Validate extracted company name is plausible and not tech/noise."""
    low = name.lower().strip()

    if low in COMPANY_NOISE:
        return False
    if len(low) < 3 or len(low) > 60:
        return False
    if "..." in name or "\u2026" in name:
        return False

    bad_starts = [
        "offer", "the best", "best ", "top ", "how ", "what ", "why ",
        "list of", "companies that", "apply", "search", "find ",
        "job ", "jobs ", "career",
    ]
    if any(low.startswith(b) for b in bad_starts):
        return False

    # Must contain at least one uppercase letter (proper noun)
    if not any(c.isupper() for c in name):
        return False

    # Reject if it looks like a tech/SaaS company
    if any(marker in low for marker in TECH_MARKERS):
        return False

    return True


def _extract_companies_from_result(result: dict) -> list[dict]:
    """Extract company name hints from a job board search result."""
    companies = []
    title = result.get("title", "")
    body = result.get("body", "")
    href = result.get("href", "")

    # --- Indeed URL patterns ------------------------------------------------
    # e.g. indeed.com/cmp/Company-Name/jobs  or  indeed.com/jobs?...&company=...
    indeed_cmp = re.search(r"indeed\.com/cmp/([^/?#]+)", href)
    if indeed_cmp:
        name = indeed_cmp.group(1).replace("-", " ").title()
        if len(name) > 2:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    # --- ZipRecruiter URL patterns ------------------------------------------
    # e.g. ziprecruiter.com/c/Company-Name/jobs
    zr_cmp = re.search(r"ziprecruiter\.com/c/([^/?#]+)", href)
    if zr_cmp:
        name = zr_cmp.group(1).replace("-", " ").title()
        if len(name) > 2:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    # --- Monster URL patterns -----------------------------------------------
    # e.g. monster.com/company/company-name
    monster_cmp = re.search(r"monster\.com/company/([^/?#]+)", href)
    if monster_cmp:
        name = monster_cmp.group(1).replace("-", " ").title()
        if len(name) > 2:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    # --- "at Company Name" pattern in titles --------------------------------
    # Common in job listing titles: "Job Title at Company Name - City"
    at_match = re.search(
        r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.,]+?)(?:\s*[-|,]|\s+in\s+Chicago|\s+\()",
        title,
    )
    if at_match:
        name = at_match.group(1).strip().rstrip(".")
        if name.lower() not in COMPANY_NOISE and len(name) > 3:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    # --- "Company Name - Job Title" pattern (Indeed titles) -----------------
    dash_match = re.search(
        r"^([A-Z][A-Za-z0-9\s&.]+?)\s*[-\u2013\u2014]\s+(?:.*?(?:job|position|hiring|role))",
        title,
        re.IGNORECASE,
    )
    if dash_match:
        name = dash_match.group(1).strip()
        if name.lower() not in COMPANY_NOISE and len(name) > 3:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    # --- "Company Name is hiring" pattern -----------------------------------
    hiring_match = re.search(r"^([A-Z][A-Za-z0-9\s&.]+?)\s+is\s+hiring", title)
    if hiring_match:
        name = hiring_match.group(1).strip()
        if name.lower() not in COMPANY_NOISE and len(name) > 3:
            companies.append({"name": name, "url": href, "evidence": body[:200]})

    return companies


class JobBoardsScraper(BaseScraper):
    """Scrape job boards via DuckDuckGo to find Chicago companies with L&D benefits."""

    name = "job_boards"
    rate_limit_seconds = 2.0

    def scrape(self) -> list[Company]:
        ddgs = DDGS()
        all_companies: dict[str, Company] = {}

        for query in JOB_BOARD_QUERIES:
            self.logger.info(f"Job boards DDG search: {query[:70]}...")
            try:
                results = list(ddgs.text(query, max_results=10))
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"DDG job board search error (skipping): {e}")
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
                    elif _is_valid_company(name):
                        all_companies[key] = Company(
                            name=name,
                            has_lnd_budget=True,
                            lnd_evidence=[comp["evidence"]],
                            lnd_source_urls=[comp["url"]],
                            sources=["job_boards"],
                            confidence_score=0.5,
                        )

        companies = list(all_companies.values())
        self.logger.info(f"Found {len(companies)} companies via job board search")
        return companies
