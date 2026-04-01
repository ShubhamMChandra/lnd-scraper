import logging
import re

from bs4 import BeautifulSoup

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class GreatPlaceToWorkScraper(BaseScraper):
    name = "greatplacetowork"
    rate_limit_seconds = 3.0

    def scrape(self) -> list[Company]:
        urls = [
            "https://www.greatplacetowork.com/best-workplaces/chicago/2025",
            "https://www.greatplacetowork.com/best-workplaces/chicago/2024",
        ]

        for url in urls:
            companies = self._scrape_list(url)
            if companies:
                return companies

        self.logger.warning("Could not scrape any Great Place to Work lists")
        return []

    def _scrape_list(self, url: str) -> list[Company]:
        companies = []
        try:
            resp = self._request(url)
            if resp.status_code != 200:
                self.logger.debug(f"HTTP {resp.status_code} for {url}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")

            # GPTW lists company names in various card/list formats
            selectors = [
                '[class*="company-name"]',
                '[class*="CompanyName"]',
                '[class*="winner"]',
                'h3[class*="name"]',
                '[data-company]',
                '.company-card',
                'article h2',
                'article h3',
            ]

            seen = set()
            for selector in selectors:
                elements = soup.select(selector)
                for el in elements:
                    name = el.get_text().strip()
                    name = re.sub(r"^\d+[\.\)]\s*", "", name)
                    name = name.split("\n")[0].strip()

                    if len(name) < 2 or len(name) > 80:
                        continue
                    if name.lower() in seen:
                        continue

                    seen.add(name.lower())
                    companies.append(Company(
                        name=name,
                        has_lnd_budget=False,
                        lnd_evidence=["Great Place to Work - Chicago certified"],
                        lnd_source_urls=[url],
                        sources=["greatplacetowork"],
                        confidence_score=0.4,
                    ))

            # If selectors didn't work, try parsing all text for company-like names
            if not companies:
                companies = self._parse_from_text(soup, url)

        except Exception as e:
            self.logger.error(f"Error scraping GPTW {url}: {e}")

        self.logger.info(f"Found {len(companies)} companies from GPTW")
        return companies

    def _parse_from_text(self, soup: BeautifulSoup, url: str) -> list[Company]:
        """Fallback: look for JSON-LD or embedded data."""
        companies = []
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        name = item.get("name", "")
                        if name:
                            companies.append(Company(
                                name=name,
                                has_lnd_budget=False,
                                lnd_evidence=["Great Place to Work - Chicago certified"],
                                lnd_source_urls=[url],
                                sources=["greatplacetowork"],
                                confidence_score=0.4,
                            ))
            except (json.JSONDecodeError, TypeError):
                continue

        return companies
