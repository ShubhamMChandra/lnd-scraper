import logging
import re
import urllib.robotparser

from bs4 import BeautifulSoup

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

LND_KEYWORDS = [
    "learning and development", "professional development",
    "education stipend", "tuition reimbursement", "training budget",
    "learning budget", "development fund", "conference budget",
    "l&d budget", "continuing education", "career development fund",
    "learning stipend", "skill development budget", "education benefit",
    "professional growth fund", "development allowance",
    "training allowance", "certification reimbursement",
    "course reimbursement", "education assistance",
    "professional development stipend", "learning allowance",
]

CAREER_PATHS = [
    "/careers",
    "/careers/benefits",
    "/benefits",
    "/about/benefits",
    "/working-here",
    "/life",
    "/culture",
    "/join",
    "/jobs",
    "/perks",
    "/about/careers",
]


class CareerPagesScraper(BaseScraper):
    name = "career_pages"
    rate_limit_seconds = 2.0

    def scrape(self) -> list[Company]:
        # This scraper is used as a confirmation pass, not standalone
        return []

    def check_lnd(self, domain: str) -> list[str]:
        """Check a company's website for L&D evidence. Returns evidence strings."""
        if not domain:
            return []

        # Check robots.txt
        if not self._can_scrape(domain):
            return []

        evidence = []
        for path in CAREER_PATHS:
            url = f"https://{domain}{path}"
            try:
                resp = self._request(url, allow_redirects=True)
                if resp.status_code != 200:
                    continue

                text = BeautifulSoup(resp.text, "html.parser").get_text().lower()
                found = self._find_lnd_evidence(text, url)
                evidence.extend(found)

                if evidence:
                    break  # Found evidence, no need to check more pages

            except Exception as e:
                self.logger.debug(f"Error checking {url}: {e}")
                continue

        return evidence

    def _find_lnd_evidence(self, text: str, url: str) -> list[str]:
        """Search page text for L&D keywords and extract context."""
        evidence = []
        for keyword in LND_KEYWORDS:
            if keyword in text:
                # Extract surrounding sentence
                idx = text.index(keyword)
                start = max(0, idx - 100)
                end = min(len(text), idx + len(keyword) + 150)
                context = text[start:end].strip()
                # Clean up whitespace
                context = re.sub(r"\s+", " ", context)
                evidence.append(f"Career page ({url}): ...{context}...")
                break  # One piece of evidence per page is enough

        return evidence

    def _can_scrape(self, domain: str) -> bool:
        """Check robots.txt."""
        try:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            rp.read()
            return rp.can_fetch("*", f"https://{domain}/careers")
        except Exception:
            return True  # If can't read robots.txt, assume OK
