import re
import logging
from typing import Optional

from serpapi import GoogleSearch

from models import HRContact

logger = logging.getLogger(__name__)


class GoogleSearchEnricher:
    def __init__(self, config: dict):
        self.api_key = config.get("serpapi_key")
        self.searches_used = 0
        self.max_searches = config.get("enrichment", {}).get("google_search", {}).get("max_searches", 50)
        self.logger = logging.getLogger("enrichment.google_search")

    def search_hr_contacts(self, company_name: str, domain: Optional[str]) -> list[HRContact]:
        if not self.api_key:
            return []

        if self.searches_used >= self.max_searches:
            self.logger.debug("Google search budget exhausted")
            return []

        contacts = []
        query = f'"{company_name}" Chicago "HR" OR "People" OR "Talent" director OR manager OR VP site:linkedin.com/in'

        try:
            search = GoogleSearch({
                "q": query,
                "num": 5,
                "api_key": self.api_key,
            })
            results = search.get_dict()
            self.searches_used += 1

            for result in results.get("organic_results", [])[:3]:
                link = result.get("link", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")

                if "linkedin.com/in/" not in link:
                    continue

                # Parse name from title: "First Last - Title - Company | LinkedIn"
                name_match = re.match(r"^(.+?)\s*[-–—|]", title)
                if not name_match:
                    continue

                full_name = name_match.group(1).strip()
                parts = full_name.split()
                if len(parts) < 2:
                    continue

                # Try to extract title from the rest
                person_title = ""
                title_match = re.search(r"[-–—]\s*(.+?)\s*[-–—]", title)
                if title_match:
                    person_title = title_match.group(1).strip()

                # Verify this is an HR-related person
                combined = f"{person_title} {snippet}".lower()
                hr_keywords = ["hr", "human resource", "people", "talent", "learning", "development", "recruit"]
                if not any(kw in combined for kw in hr_keywords):
                    continue

                contacts.append(HRContact(
                    company_name=company_name,
                    company_domain=domain,
                    first_name=parts[0],
                    last_name=" ".join(parts[1:]),
                    full_name=full_name,
                    title=person_title or None,
                    linkedin_url=link,
                    source="google_search",
                ))

        except Exception as e:
            self.logger.error(f"Google search error for {company_name}: {e}")

        return contacts
