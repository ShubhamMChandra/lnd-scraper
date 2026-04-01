import logging
import re
import time
import random
import json
from urllib.parse import urlparse

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class BuiltInChicagoScraper(BaseScraper):
    name = "builtin_chicago"
    rate_limit_seconds = 3.0

    def scrape(self) -> list[Company]:
        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
        except ImportError:
            self.logger.error("Playwright not installed. Run: pip install playwright playwright-stealth && playwright install chromium")
            return []

        companies: dict[str, Company] = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            stealth = Stealth()
            stealth.use_sync(context)
            page = context.new_page()

            try:
                self._scrape_company_list(page, companies)
            except Exception as e:
                self.logger.error(f"Error scraping Built In Chicago list: {e}")

            browser.close()

        result = list(companies.values())
        self.logger.info(f"Found {len(result)} companies on Built In Chicago")
        return result

    def _scrape_company_list(self, page, companies: dict):
        base_url = "https://builtin.com/companies?search=&industry=&perk=continuing-education-stipend%2Ctuition-reimbursement%2Cjob-training-conferences&city=Chicago"

        self.logger.info(f"Loading Built In Chicago: {base_url}")
        page.goto(base_url, wait_until="networkidle", timeout=60000)
        time.sleep(random.uniform(3, 5))

        page_num = 1
        max_pages = 25

        while page_num <= max_pages:
            self.logger.info(f"Processing page {page_num}")

            # Find all links to company profile pages: /company/<slug>
            links = page.query_selector_all('a[href*="/company/"]')

            company_links = {}
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip()

                # Only process direct company links like /company/slug (not /company/slug/jobs etc.)
                match = re.match(r"^(?:https://builtin\.com)?/company/([a-z0-9-]+)$", href)
                if not match:
                    continue

                slug = match.group(1)

                # Filter out noise: numbers, very short text, generic words
                if not text or len(text) < 2 or len(text) > 80:
                    continue
                if re.match(r"^\d+\s*(Benefits|Jobs|Offices)", text):
                    continue
                if text.lower() in ("view", "see more", "learn more", "apply"):
                    continue

                if slug not in company_links:
                    company_links[slug] = {"name": text, "href": href, "slug": slug}

            self.logger.info(f"  Found {len(company_links)} company links on page {page_num}")

            for slug, info in company_links.items():
                name = info["name"]
                key = name.lower()
                if key in companies:
                    continue

                profile_url = f"https://builtin.com/company/{slug}"
                companies[key] = Company(
                    name=name,
                    has_lnd_budget=True,
                    lnd_evidence=["Listed on Built In Chicago with L&D filters (continuing education, tuition reimbursement, job training)"],
                    lnd_source_urls=[profile_url],
                    sources=["builtin_chicago"],
                    confidence_score=0.8,
                )

            # Try pagination
            next_btn = page.query_selector('a[rel="next"], [class*="pager"] a:has-text("Next"), a:has-text("Next page"), a[aria-label="Next page"]')
            if next_btn:
                try:
                    next_btn.click()
                    time.sleep(random.uniform(3, 5))
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page_num += 1
                except Exception as e:
                    self.logger.debug(f"Pagination failed: {e}")
                    break
            else:
                # Try scroll-based loading
                prev_count = len(companies)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(3, 5))
                if len(companies) == prev_count:
                    break
                page_num += 1
