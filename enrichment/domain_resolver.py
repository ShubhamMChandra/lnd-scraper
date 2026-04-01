"""Resolve company domains using Google search + DDG fallback."""
import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

from ddgs import DDGS

logger = logging.getLogger(__name__)


class DomainResolver:
    def __init__(self, config: dict):
        self.api_key = config.get("serpapi_key")
        self.searches_used = 0
        self.max_searches = 100  # Reserve from the 250/month budget
        self.cache: dict[str, Optional[str]] = {}
        self._ddgs = None

    def _get_ddgs(self):
        if self._ddgs is None:
            self._ddgs = DDGS()
        return self._ddgs

    def resolve(self, company_name: str) -> Optional[str]:
        """Find the main domain for a company. Tries SerpAPI first, falls back to DDG."""
        key = company_name.lower().strip()
        if key in self.cache:
            return self.cache[key]

        # Try SerpAPI first if available
        if self.api_key and self.searches_used < self.max_searches:
            try:
                from serpapi import GoogleSearch
                search = GoogleSearch({
                    "q": f'"{company_name}" Chicago official site',
                    "num": 5,
                    "api_key": self.api_key,
                })
                results = search.get_dict()
                self.searches_used += 1

                for result in results.get("organic_results", []):
                    link = result.get("link", "")
                    domain = self._extract_domain(link)
                    if domain and not self._is_noise_domain(domain):
                        self.cache[key] = domain
                        logger.debug(f"Resolved {company_name} -> {domain}")
                        return domain

                kg = results.get("knowledge_graph", {})
                website = kg.get("website")
                if website:
                    domain = self._extract_domain(website)
                    if domain:
                        self.cache[key] = domain
                        return domain
            except Exception as e:
                logger.debug(f"SerpAPI domain resolution error for {company_name}: {e}")

        # Fall back to DDG (free, unlimited)
        return self._resolve_ddg(company_name, key)

    def _resolve_ddg(self, company_name: str, key: str) -> Optional[str]:
        """Resolve domain using DuckDuckGo search (free)."""
        try:
            ddgs = self._get_ddgs()
            results = list(ddgs.text(f'"{company_name}" Chicago company official website', max_results=5))
            time.sleep(1.5)

            for result in results:
                href = result.get("href", "")
                domain = self._extract_domain(href)
                if domain and not self._is_noise_domain(domain):
                    # Verify the company name appears in the result
                    title = result.get("title", "").lower()
                    body = result.get("body", "").lower()
                    name_words = company_name.lower().split()
                    # At least one significant word from company name should appear
                    if any(w in title or w in body for w in name_words if len(w) > 2):
                        self.cache[key] = domain
                        logger.debug(f"DDG resolved {company_name} -> {domain}")
                        return domain

        except Exception as e:
            logger.debug(f"DDG domain resolution error for {company_name}: {e}")

        self.cache[key] = None
        return None

    def _extract_domain(self, url: str) -> Optional[str]:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain if domain else None
        except Exception:
            return None

    def _is_noise_domain(self, domain: str) -> bool:
        noise = [
            "glassdoor.com", "indeed.com", "linkedin.com", "builtin.com",
            "ziprecruiter.com", "google.com", "yelp.com", "facebook.com",
            "twitter.com", "wikipedia.org", "reddit.com", "youtube.com",
            "crunchbase.com", "bloomberg.com", "bbb.org", "manta.com",
            "dnb.com", "zoominfo.com", "apollo.io",
        ]
        return any(domain.endswith(n) for n in noise)
