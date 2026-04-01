"""
Association & Workforce Development scraper.

Finds Chicago companies through industry association member directories,
conference sponsors, and workforce development program participants.
Uses DuckDuckGo (free, no API key).

ICP: middle-market (50-750 employees), traditional industries in Chicago.
NOT tech/AI/SaaS.
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
# Search queries grouped by category.
# Each entry: (query, industry, association_label, is_workforce_dev)
# ---------------------------------------------------------------------------
ASSOCIATION_QUERIES = [
    # Healthcare
    (
        "Illinois Hospital Association member hospitals Chicago",
        "Healthcare",
        "Illinois Hospital Association",
        False,
    ),
    (
        "Chicago healthcare employers association members",
        "Healthcare",
        "Chicago Healthcare Association",
        False,
    ),
    (
        "Illinois health care workforce development employers",
        "Healthcare",
        "Illinois Healthcare Workforce Development",
        True,
    ),
    # Manufacturing
    (
        "Illinois Manufacturers Association member companies",
        "Manufacturing",
        "Illinois Manufacturers Association",
        False,
    ),
    (
        "Technology & Manufacturing Association Chicago members",
        "Manufacturing",
        "Technology & Manufacturing Association",
        False,
    ),
    (
        "site:ima-net.org member directory",
        "Manufacturing",
        "IMA (ima-net.org)",
        False,
    ),
    # Construction
    (
        "Associated General Contractors Illinois member directory",
        "Construction",
        "Associated General Contractors of Illinois",
        False,
    ),
    (
        "Chicagoland AGC member companies",
        "Construction",
        "Chicagoland AGC",
        False,
    ),
    (
        "Illinois construction companies association",
        "Construction",
        "Illinois Construction Association",
        False,
    ),
    # Accounting
    (
        "Illinois CPA Society member firms Chicago",
        "Accounting",
        "Illinois CPA Society",
        False,
    ),
    (
        "Chicago accounting firms directory",
        "Accounting",
        "Chicago Accounting Directory",
        False,
    ),
    # Law
    (
        "Chicago Bar Association member law firms",
        "Legal",
        "Chicago Bar Association",
        False,
    ),
    (
        "Illinois State Bar Association Chicago firms",
        "Legal",
        "Illinois State Bar Association",
        False,
    ),
    # Financial Services
    (
        "Illinois Bankers Association member banks Chicago",
        "Financial Services",
        "Illinois Bankers Association",
        False,
    ),
    (
        "Chicago financial services companies association",
        "Financial Services",
        "Chicago Financial Services Association",
        False,
    ),
    # Real Estate
    (
        "Chicago Association of Realtors member companies",
        "Real Estate",
        "Chicago Association of Realtors",
        False,
    ),
    (
        "Chicago commercial real estate firms",
        "Real Estate",
        "Chicago Commercial Real Estate Directory",
        False,
    ),
    # Nonprofits
    (
        "Forefront Illinois nonprofit members Chicago",
        "Nonprofit",
        "Forefront Illinois",
        False,
    ),
    (
        "Chicago nonprofit employers association",
        "Nonprofit",
        "Chicago Nonprofit Association",
        False,
    ),
    # Logistics
    (
        "Illinois trucking association member companies Chicago",
        "Logistics",
        "Illinois Trucking Association",
        False,
    ),
    (
        "Chicago logistics companies directory",
        "Logistics",
        "Chicago Logistics Directory",
        False,
    ),
    # Workforce Development (strong L&D signal) --------------------------------
    (
        "Chicago Cook Workforce Partnership employer partners",
        "Workforce Development",
        "Chicago Cook Workforce Partnership",
        True,
    ),
    (
        "City Colleges Chicago corporate training partners",
        "Education/Training",
        "City Colleges of Chicago",
        True,
    ),
    (
        "Illinois workNet employer partners Chicago",
        "Workforce Development",
        "Illinois workNet",
        True,
    ),
    (
        "DCEO employer training investment program Illinois recipients",
        "Workforce Development",
        "DCEO Employer Training Investment Program",
        True,
    ),
    (
        "ATD Chicago chapter member companies",
        "Training & Development",
        "ATD Chicago Chapter",
        True,
    ),
    (
        "SHRM Chicago chapter sponsor companies",
        "Human Resources",
        "SHRM Chicago Chapter",
        True,
    ),
    # Extra workforce / apprenticeship queries
    (
        "Illinois apprenticeship program employer partners Chicago",
        "Workforce Development",
        "Illinois Apprenticeship Programs",
        True,
    ),
    (
        "Chicago workforce development board employer partners",
        "Workforce Development",
        "Chicago Workforce Development Board",
        True,
    ),
    (
        "ICCB corporate training partners Illinois Chicago",
        "Education/Training",
        "ICCB Corporate Training",
        True,
    ),
]

# Words/phrases that are definitely not company names
NOISE_WORDS = {
    "chicago", "illinois", "association", "member", "members", "directory",
    "home", "about", "contact", "login", "join", "resources", "search",
    "news", "events", "board", "annual", "report", "meeting", "conference",
    "glassdoor", "indeed", "linkedin", "ziprecruiter", "google", "facebook",
    "twitter", "wikipedia", "reddit", "yelp", "pinterest",
    "the best", "top companies", "how to", "what is", "our members",
    "member list", "member directory", "find a member", "page not found",
}

# Tech/SaaS signals to reject (ICP exclusion)
TECH_SIGNALS = re.compile(
    r"\b(saas|fintech|ai platform|machine learning startup|crypto|blockchain|"
    r"software as a service|devops|cloud native)\b",
    re.IGNORECASE,
)


def _is_valid_company_name(name: str) -> bool:
    """Validate that a string looks like a real company name."""
    name = name.strip()
    low = name.lower()

    if len(name) < 3 or len(name) > 50:
        return False
    if low in NOISE_WORDS:
        return False
    if "..." in name or "\u2026" in name:
        return False
    # Must start with an uppercase letter or digit
    if not (name[0].isupper() or name[0].isdigit()):
        return False
    # Must have at least one letter
    if not re.search(r"[A-Za-z]", name):
        return False
    # Reject strings that are mostly punctuation
    alpha_ratio = sum(c.isalpha() or c.isspace() for c in name) / len(name)
    if alpha_ratio < 0.6:
        return False
    # Reject common non-company starts
    bad_starts = [
        "click here", "learn more", "read more", "view all", "see all",
        "sign up", "log in", "download", "subscribe", "follow us",
        "the best", "top ", "how ", "what ", "why ", "list of",
        "companies that", "our ", "find a",
    ]
    if any(low.startswith(b) for b in bad_starts):
        return False
    # Reject tech/SaaS
    if TECH_SIGNALS.search(name):
        return False

    return True


def _extract_names_from_html(html: str, max_names: int = 30) -> list[str]:
    """Parse HTML and pull plausible company names from lists, tables, headings."""
    soup = BeautifulSoup(html, "lxml")
    candidates: list[str] = []

    # Look in <li>, <td>, <h3>, <h4>, <strong> tags -- typical for member lists
    for tag in soup.find_all(["li", "td", "h3", "h4", "strong"]):
        text = tag.get_text(separator=" ", strip=True)
        # Only take the first line / short text -- skip paragraphs
        if not text or len(text) > 80:
            continue
        # Strip trailing punctuation like ":" or " -"
        text = re.sub(r"[\s:,\-]+$", "", text).strip()
        if _is_valid_company_name(text):
            candidates.append(text)
        if len(candidates) >= max_names:
            break

    return candidates


def _extract_names_from_snippet(title: str, body: str, href: str) -> list[str]:
    """Extract plausible company names from DDG result title/body/URL."""
    names: list[str] = []

    # ---- Title-based extraction ----
    # "Company Name | Association" or "Company Name - Association"
    parts = re.split(r"\s*[|\-\u2013\u2014]\s*", title)
    for part in parts:
        part = part.strip()
        if _is_valid_company_name(part):
            names.append(part)

    # ---- Body-based extraction ----
    # Look for patterns: "Company Name, Chicago" or "Company Name (Chicago)"
    for m in re.finditer(
        r"([A-Z][A-Za-z0-9&',.\s]{2,45})(?:\s*[,\(]\s*Chicago)",
        body,
    ):
        cand = m.group(1).strip().rstrip(",. ")
        if _is_valid_company_name(cand):
            names.append(cand)

    # ---- URL-based extraction ----
    # /members/company-slug or /company/company-slug
    url_match = re.search(
        r"/(?:members?|company|firms?|sponsor|partner)[/-]([a-z0-9\-]{3,40})",
        href,
        re.IGNORECASE,
    )
    if url_match:
        slug = url_match.group(1).replace("-", " ").title()
        if _is_valid_company_name(slug):
            names.append(slug)

    return names


class AssociationsScraper(BaseScraper):
    """Discover Chicago companies via industry association directories and
    workforce development program participant lists using DuckDuckGo."""

    name = "associations"
    rate_limit_seconds = 3.0

    def scrape(self) -> list[Company]:
        ddgs = DDGS()
        seen: dict[str, Company] = {}  # keyed by lowercased name

        for query, industry, assoc_label, is_workforce in ASSOCIATION_QUERIES:
            self.logger.info(f"[associations] Searching: {query[:70]}...")

            # ---------- DDG text search ----------
            try:
                results = list(ddgs.text(query, max_results=10))
                time.sleep(self.rate_limit_seconds)
            except Exception as e:
                self.logger.warning(f"DDG search error, skipping query: {e}")
                time.sleep(4)
                continue

            if not results:
                self.logger.debug(f"No DDG results for: {query[:60]}")
                continue

            # Collect (name, url, evidence) tuples from this query
            found: list[tuple[str, str, str]] = []

            for result in results:
                title = result.get("title", "")
                body = result.get("body", "")
                href = result.get("href", "")

                # Extract from title/body/URL
                snippet_names = _extract_names_from_snippet(title, body, href)
                for n in snippet_names:
                    found.append((n, href, body[:200]))

                # Try to fetch and parse the actual page for member lists
                if href and len(found) < 50:
                    page_names = self._fetch_and_parse_page(href)
                    for n in page_names:
                        found.append((n, href, f"Found on page: {href}"))

            # Deduplicate and store
            for name, url, evidence in found:
                key = name.lower().strip()
                if key in seen:
                    existing = seen[key]
                    ev = (
                        f"Workforce development partner: {assoc_label}"
                        if is_workforce
                        else f"Member of {assoc_label}"
                    )
                    if ev not in existing.lnd_evidence:
                        existing.lnd_evidence.append(ev)
                    if url and url not in existing.lnd_source_urls:
                        existing.lnd_source_urls.append(url)
                    # Upgrade confidence if workforce source
                    if is_workforce and existing.confidence_score < 0.6:
                        existing.confidence_score = 0.6
                        existing.has_lnd_budget = True
                else:
                    if is_workforce:
                        ev = f"Workforce development partner: {assoc_label}"
                        conf = 0.6
                        has_lnd = True
                    else:
                        ev = f"Member of {assoc_label}"
                        conf = 0.3
                        has_lnd = False

                    seen[key] = Company(
                        name=name,
                        industry=industry,
                        has_lnd_budget=has_lnd,
                        lnd_evidence=[ev],
                        lnd_source_urls=[url] if url else [],
                        sources=["associations"],
                        confidence_score=conf,
                    )

        companies = list(seen.values())
        self.logger.info(
            f"[associations] Found {len(companies)} companies "
            f"across {len(ASSOCIATION_QUERIES)} queries"
        )
        self.save_raw(companies)
        return companies

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_and_parse_page(self, url: str) -> list[str]:
        """Attempt to fetch a URL and extract company names from HTML."""
        try:
            resp = self._request(url)
            if resp is None or resp.status_code != 200:
                return []
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type:
                return []
            return _extract_names_from_html(resp.text, max_names=30)
        except Exception as e:
            self.logger.debug(f"Could not parse page {url}: {e}")
            return []
