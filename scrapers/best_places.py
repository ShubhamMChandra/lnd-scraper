"""
Best Places to Work list aggregator for Chicago.

Searches DuckDuckGo for multiple "Best Places to Work" lists and
industry association member directories targeting Chicago middle-market
companies (50-750 employees) in traditional industries. Companies on
these lists invest in employees and are likely L&D budget holders.

Free — no API key required (uses ddgs library).
"""

import logging
import re
import time

from bs4 import BeautifulSoup

from ddgs import DDGS
from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search queries — "Best Places to Work" lists + industry association members
# ---------------------------------------------------------------------------
BEST_PLACES_QUERIES = [
    # --- Best Places to Work lists ---
    "Chicago Tribune Top Workplaces 2024 2025 list",
    "Chicago Tribune Top Workplaces midsize companies 2024",
    "Best and Brightest Companies to Work For Chicago 2024 2025",
    "Training Magazine Training Top 125 Chicago companies",
    "Modern Healthcare Best Places to Work 2024 Chicago",
    "American Lawyer Best Law Firms to Work For Chicago 2024",
    "Fortune Best Workplaces Chicago 2024 2025",
    "Fortune Best Small and Medium Workplaces Chicago",
    "Chicago Business Journal Best Places to Work 2024",
    "Crain's Chicago Business Best Places to Work 2024 2025",
    "SHRM Chicago Best Employers 2024",
    "Glassdoor Best Places to Work Chicago midsize 2024",
    "BuiltIn Chicago Best Places to Work midsize 2024 2025",
    "Great Place to Work Certified Chicago companies 2024",
    "Inc. Best Workplaces Chicago 2024 midsize company",

    # --- Industry association member directories ---
    "ATD Association for Talent Development Chicago chapter sponsors members",
    "ATD Chicagoland chapter member companies",
    "Illinois Manufacturers Association member companies Chicago",
    "Associated General Contractors Illinois member contractors Chicago",
    "Illinois CPA Society member firms Chicago",
    "Chicago Bar Association member firms directory",
    "Illinois Hospital Association member hospitals Chicago",
    "Chicagoland Chamber of Commerce member companies list",
    "Illinois Bankers Association member banks Chicago",

    # --- Niche / industry-specific best-of lists ---
    "best healthcare employers Chicago 2024",
    "best manufacturing companies to work for Chicago Illinois",
    "best accounting firms to work for Chicago 2024",
    "best construction companies to work for Chicago Illinois",
    "best nonprofit employers Chicago 2024 2025",
    "best financial services companies to work for Chicago 2024",
]

# ---------------------------------------------------------------------------
# Noise filtering (mirrors ddg_search.py)
# ---------------------------------------------------------------------------
COMPANY_NOISE = {
    "chicago", "glassdoor", "indeed", "linkedin", "builtin", "ziprecruiter",
    "google", "yelp", "facebook", "twitter", "wikipedia", "reddit",
    "we offer", "work", "budget", "stipend", "professional development",
    "learning and development", "training", "companies", "employer",
    "offer", "startups", "lmi", "home page", "page", "best places",
    "top workplaces", "fortune", "crain", "tribune", "youtube",
    "instagram", "tiktok", "pinterest", "amazon", "apple", "microsoft",
    "duckduckgo", "about", "contact", "careers", "login", "sign up",
    "associated general contractors", "illinois manufacturers",
    "best and brightest", "shrm", "atd", "association",
    "the national", "bureau of labor", "u.s. department",
}

# Additional reject patterns for snippet-like strings
_BAD_STARTS = (
    "offer", "the best", "best ", "top ", "how ", "what ", "why ",
    "list of", "companies that", "startups", "here are", "these ",
    "find ", "search", "view ", "see ", "learn ", "click ",
    "our ", "your ", "this ", "that ", "about ", "the top",
    "in ", "at ", "with ", "from ", "for ",
)


def _is_valid_company_name(name: str) -> bool:
    """Return True if *name* looks like a real company name."""
    clean = name.strip()
    low = clean.lower()

    if low in COMPANY_NOISE:
        return False
    if len(clean) < 3 or len(clean) > 60:
        return False
    # Reject snippet fragments
    if "..." in clean or "\u2026" in clean:
        return False
    if any(low.startswith(b) for b in _BAD_STARTS):
        return False
    # Must have at least one uppercase letter (proper noun)
    if not any(c.isupper() for c in clean):
        return False
    # Reject if it is all digits / punctuation
    if not re.search(r"[A-Za-z]{2,}", clean):
        return False
    # Reject very generic single words
    if " " not in clean and low in {
        "company", "firm", "group", "partners", "hospital",
        "bank", "agency", "services", "solutions", "inc",
        "corp", "llc", "ltd", "associates", "consulting",
    }:
        return False
    return True


def _clean_company_name(raw: str) -> str:
    """Light normalization: strip surrounding punctuation/numbers."""
    name = raw.strip()
    # Remove leading numbering like "1. ", "12) ", "# "
    name = re.sub(r"^[\d#]+[.):\-\s]+", "", name).strip()
    # Remove trailing punctuation
    name = re.sub(r"[,;:\-|]+$", "", name).strip()
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)
    return name


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_names_from_ddg_results(results: list[dict]) -> list[dict]:
    """Pull candidate company names from DDG text-search results."""
    found: list[dict] = []

    for result in results:
        title = result.get("title", "")
        body = result.get("body", "")
        href = result.get("href", "")

        # --- URL-based extraction ---
        # BuiltIn company pages
        m = re.search(r"builtin\.com/company/([^/?#]+)", href)
        if m:
            name = _clean_company_name(m.group(1).replace("-", " ").title())
            if _is_valid_company_name(name):
                found.append({"name": name, "url": href, "snippet": body[:200]})

        # Glassdoor company reviews
        m = re.search(r"glassdoor\.com/Reviews/([^-]+)-Reviews", href)
        if m:
            name = _clean_company_name(m.group(1).replace("-", " ").title())
            if _is_valid_company_name(name):
                found.append({"name": name, "url": href, "snippet": body[:200]})

        # --- Title-based patterns ---
        # "Company Name | Best Places …"  /  "Company Name - …"
        m = re.match(r"^([A-Z][A-Za-z0-9&',.\s]+?)(?:\s*[-|:–—])", title)
        if m:
            name = _clean_company_name(m.group(1))
            if _is_valid_company_name(name):
                found.append({"name": name, "url": href, "snippet": body[:200]})

        # "at Company Name" in title
        m = re.search(
            r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.']+?)(?:\s*[-|,]|\s+in\s+Chicago)",
            title,
        )
        if m:
            name = _clean_company_name(m.group(1))
            if _is_valid_company_name(name):
                found.append({"name": name, "url": href, "snippet": body[:200]})

        # --- Body / snippet patterns ---
        # Numbered list entries: "1. Acme Corp" or "1) Acme Corp"
        for m in re.finditer(
            r"(?:^|\n)\s*\d{1,3}[.)]\s+([A-Z][A-Za-z0-9&',.\s]{2,40})", body
        ):
            name = _clean_company_name(m.group(1))
            if _is_valid_company_name(name):
                found.append({"name": name, "url": href, "snippet": body[:200]})

        # Bullet / dash list entries: "- Acme Corp" or "• Acme Corp"
        for m in re.finditer(
            r"(?:^|\n)\s*[-•]\s+([A-Z][A-Za-z0-9&',.\s]{2,40})", body
        ):
            name = _clean_company_name(m.group(1))
            if _is_valid_company_name(name):
                found.append({"name": name, "url": href, "snippet": body[:200]})

    return found


def _extract_names_from_html(html: str, url: str) -> list[dict]:
    """Scrape company names from a fetched list page."""
    found: list[dict] = []
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return found

    # Look inside <li>, <h2>, <h3>, <h4>, <td>, <strong> elements
    selectors = ["li", "h2", "h3", "h4", "td", "strong", "b"]
    for tag_name in selectors:
        for el in soup.find_all(tag_name):
            text = el.get_text(separator=" ", strip=True)
            if not text:
                continue
            # Take only the first line / first 60 chars
            candidate = text.split("\n")[0][:60].strip()
            candidate = _clean_company_name(candidate)
            if _is_valid_company_name(candidate):
                found.append({"name": candidate, "url": url, "snippet": ""})

    return found


# ---------------------------------------------------------------------------
# Scraper class
# ---------------------------------------------------------------------------

class BestPlacesScraper(BaseScraper):
    """Aggregate multiple 'Best Places to Work' lists for Chicago via DDG."""

    name = "best_places"
    rate_limit_seconds = 2.0

    # Number of DDG text results to fetch per query
    MAX_DDG_RESULTS = 12
    # Max pages to actually fetch & scrape per run (avoid hammering)
    MAX_PAGE_SCRAPES = 20

    def scrape(self) -> list[Company]:
        ddgs = DDGS()
        all_companies: dict[str, dict] = {}  # keyed by lowercase name
        pages_scraped = 0

        for query in BEST_PLACES_QUERIES:
            self.logger.info(f"[best_places] DDG search: {query[:70]}...")
            try:
                results = list(ddgs.text(query, max_results=self.MAX_DDG_RESULTS))
                time.sleep(2)  # rate limit between DDG calls
            except Exception as e:
                self.logger.warning(f"DDG search error (skipping): {e}")
                time.sleep(3)
                continue

            # --- Phase 1: extract from DDG snippets / titles ---
            extracted = _extract_names_from_ddg_results(results)
            for item in extracted:
                self._merge(all_companies, item, query)

            # --- Phase 2: scrape promising result pages ---
            if pages_scraped >= self.MAX_PAGE_SCRAPES:
                continue

            for result in results:
                if pages_scraped >= self.MAX_PAGE_SCRAPES:
                    break
                href = result.get("href", "")
                if not href or not href.startswith("http"):
                    continue
                # Only scrape pages that look like list articles
                low_title = result.get("title", "").lower()
                low_body = result.get("body", "").lower()
                is_list_page = any(
                    kw in low_title or kw in low_body
                    for kw in [
                        "top workplaces", "best places", "best companies",
                        "member", "directory", "list", "winners",
                        "best and brightest", "certified",
                    ]
                )
                if not is_list_page:
                    continue

                time.sleep(3)  # rate limit before page scrape
                try:
                    resp = self._request(href)
                    if resp.status_code != 200:
                        continue
                    # Only parse HTML responses
                    ctype = resp.headers.get("Content-Type", "")
                    if "html" not in ctype:
                        continue
                    page_extracted = _extract_names_from_html(resp.text, href)
                    for item in page_extracted:
                        self._merge(all_companies, item, query)
                    pages_scraped += 1
                    self.logger.info(
                        f"  Scraped page ({pages_scraped}/{self.MAX_PAGE_SCRAPES}): "
                        f"{href[:80]}... -> {len(page_extracted)} candidates"
                    )
                except Exception as e:
                    self.logger.warning(f"Page scrape failed ({href[:60]}): {e}")

        # Build Company objects
        companies = self._build_companies(all_companies)
        self.logger.info(
            f"[best_places] Total unique companies: {len(companies)}"
        )
        return companies

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge(
        self,
        store: dict[str, dict],
        item: dict,
        query: str,
    ) -> None:
        """Merge an extracted item into the de-duplicated store."""
        key = item["name"].lower().strip()
        if key in store:
            entry = store[key]
            if item.get("url") and item["url"] not in entry["urls"]:
                entry["urls"].append(item["url"])
            if query not in entry["queries"]:
                entry["queries"].append(query)
        else:
            store[key] = {
                "name": item["name"],
                "urls": [item["url"]] if item.get("url") else [],
                "queries": [query],
                "snippet": item.get("snippet", ""),
            }

    def _build_companies(self, store: dict[str, dict]) -> list[Company]:
        """Convert the internal store into a list of Company objects."""
        companies: list[Company] = []
        for entry in store.values():
            evidence = []
            for q in entry["queries"]:
                evidence.append(f"Named in best places to work list: {q}")

            companies.append(
                Company(
                    name=entry["name"],
                    has_lnd_budget=False,
                    lnd_evidence=evidence,
                    lnd_source_urls=entry["urls"],
                    sources=["best_places"],
                    confidence_score=0.4,
                )
            )
        return companies
