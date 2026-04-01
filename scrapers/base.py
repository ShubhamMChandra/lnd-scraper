import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod

import requests

from models import Company

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    name: str = "base"
    rate_limit_seconds: float = 2.0
    max_retries: int = 3

    def __init__(self, config: dict):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.logger = logging.getLogger(f"scraper.{self.name}")
        self._last_request_time = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            jitter = random.uniform(0, 0.5)
            time.sleep(self.rate_limit_seconds - elapsed + jitter)
        self._last_request_time = time.time()

    def _request(self, url: str, **kwargs) -> requests.Response:
        self._rate_limit()
        self.session.headers["User-Agent"] = random.choice(USER_AGENTS)

        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, timeout=30, **kwargs)
                if resp.status_code == 429:
                    wait = 30 * (attempt + 1)
                    self.logger.warning(f"Rate limited on {url}, waiting {wait}s")
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    wait = 5 * (attempt + 1)
                    self.logger.warning(f"Server error {resp.status_code} on {url}, retrying in {wait}s")
                    time.sleep(wait)
                    continue
                return resp
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Failed after {self.max_retries} retries: {url} - {e}")
                    raise
                wait = 5 * (attempt + 1)
                self.logger.warning(f"Request error on {url}: {e}, retrying in {wait}s")
                time.sleep(wait)

        return resp

    def save_raw(self, companies: list[Company]):
        raw_dir = self.config.get("raw_dir", "data/raw")
        os.makedirs(raw_dir, exist_ok=True)
        path = os.path.join(raw_dir, f"{self.name}.json")
        data = [c.to_dict() for c in companies]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved {len(companies)} companies to {path}")

    @abstractmethod
    def scrape(self) -> list[Company]:
        pass
