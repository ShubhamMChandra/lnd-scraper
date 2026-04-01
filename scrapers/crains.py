import logging
import re

from bs4 import BeautifulSoup
from serpapi import GoogleSearch

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class CrainsScraper(BaseScraper):
    name = "crains"
    rate_limit_seconds = 3.0

    def scrape(self) -> list[Company]:
        api_key = self.config.get("serpapi_key")
        companies = []

        # Step 1: Find the latest Crain's Best Places to Work list via SerpAPI
        if api_key:
            companies.extend(self._search_via_serpapi(api_key))

        # Step 2: Try to scrape known Crain's URLs directly
        companies.extend(self._scrape_known_urls())

        self.logger.info(f"Found {len(companies)} companies from Crain's")
        return companies

    def _search_via_serpapi(self, api_key: str) -> list[Company]:
        companies = []
        try:
            search = GoogleSearch({
                "q": 'site:chicagobusiness.com "best places to work" 2025 OR 2024 Chicago list',
                "num": 10,
                "api_key": api_key,
            })
            results = search.get_dict()
            organic = results.get("organic_results", [])

            for result in organic:
                link = result.get("link", "")
                if "best-places" in link or "best-workplaces" in link:
                    self.logger.info(f"Found Crain's list at: {link}")
                    page_companies = self._scrape_list_page(link)
                    companies.extend(page_companies)
                    if page_companies:
                        break
        except Exception as e:
            self.logger.error(f"SerpAPI search for Crain's failed: {e}")

        return companies

    def _scrape_known_urls(self) -> list[Company]:
        urls = [
            "https://www.chicagobusiness.com/awards/best-places-work-chicago-2025",
            "https://www.chicagobusiness.com/awards/best-places-work-chicago-2024",
        ]
        for url in urls:
            try:
                companies = self._scrape_list_page(url)
                if companies:
                    return companies
            except Exception as e:
                self.logger.debug(f"Could not scrape {url}: {e}")
        return []

    def _scrape_list_page(self, url: str) -> list[Company]:
        companies = []
        try:
            resp = self._request(url)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text()

            # Look for company names in list patterns
            # Crain's lists typically have numbered entries or cards
            cards = soup.select('[class*="company"], [class*="winner"], [class*="honoree"], li, h3, h4')

            seen = set()
            for card in cards:
                name = card.get_text().strip()
                # Clean up: remove numbers, rankings, descriptions
                name = re.sub(r"^\d+[\.\)]\s*", "", name)
                name = name.split("\n")[0].strip()

                if len(name) < 3 or len(name) > 80:
                    continue
                if name.lower() in seen:
                    continue

                # Filter out non-company text
                skip_words = ["best places", "winner", "about", "read more", "chicago", "crain"]
                if any(sw in name.lower() for sw in skip_words):
                    continue

                seen.add(name.lower())
                companies.append(Company(
                    name=name,
                    has_lnd_budget=False,  # needs confirmation
                    lnd_evidence=[f"Crain's Best Places to Work Chicago"],
                    lnd_source_urls=[url],
                    sources=["crains"],
                    confidence_score=0.4,
                ))

        except Exception as e:
            self.logger.error(f"Error scraping Crain's page {url}: {e}")

        return companies
