"""Resolve company domains using Google search."""
import logging
import re
from typing import Optional
from urllib.parse import urlparse

from serpapi import GoogleSearch

logger = logging.getLogger(__name__)


class DomainResolver:
    def __init__(self, config: dict):
        self.api_key = config.get("serpapi_key")
        self.searches_used = 0
        self.max_searches = 100  # Reserve from the 250/month budget
        self.cache: dict[str, Optional[str]] = {}

    def resolve(self, company_name: str) -> Optional[str]:
        """Find the main domain for a company."""
        key = company_name.lower().strip()
        if key in self.cache:
            return self.cache[key]

        if not self.api_key or self.searches_used >= self.max_searches:
            return None

        try:
            search = GoogleSearch({
                "q": f'"{company_name}" Chicago official site',
                "num": 5,
                "api_key": self.api_key,
            })
            results = search.get_dict()
            self.searches_used += 1

            # Check organic results for a company domain
            for result in results.get("organic_results", []):
                link = result.get("link", "")
                domain = self._extract_domain(link)
                if domain and not self._is_noise_domain(domain):
                    self.cache[key] = domain
                    logger.debug(f"Resolved {company_name} -> {domain}")
                    return domain

            # Check knowledge graph
            kg = results.get("knowledge_graph", {})
            website = kg.get("website")
            if website:
                domain = self._extract_domain(website)
                if domain:
                    self.cache[key] = domain
                    return domain

        except Exception as e:
            logger.error(f"Domain resolution error for {company_name}: {e}")

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
