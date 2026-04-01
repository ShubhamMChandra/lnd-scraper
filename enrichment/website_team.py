import re
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

from models import HRContact

logger = logging.getLogger(__name__)

TEAM_PATHS = [
    "/about/team", "/about/leadership", "/about", "/team",
    "/our-team", "/people", "/leadership", "/about-us",
    "/company/team", "/company/leadership",
]

HR_TITLE_PATTERNS = [
    r"(?:chief\s+people|chief\s+human|head\s+of\s+(?:people|hr|human)|vp\s+(?:of\s+)?(?:people|human|hr|talent))",
    r"(?:director|manager|lead)\s+(?:of\s+)?(?:hr|human\s+resource|people|talent|learning|l&d|training)",
    r"(?:hr|human\s+resource)\s+(?:director|manager|vp|head|lead)",
    r"(?:people\s+operations|talent\s+(?:acquisition|development))\s+(?:director|manager|lead|head)",
]


class WebsiteTeamEnricher:
    def __init__(self, config: dict):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.logger = logging.getLogger("enrichment.website_team")

    def search_hr_contacts(self, company_name: str, domain: Optional[str]) -> list[HRContact]:
        if not domain:
            return []

        contacts = []
        for path in TEAM_PATHS:
            url = f"https://{domain}{path}"
            try:
                resp = self.session.get(url, timeout=15, allow_redirects=True)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                found = self._extract_hr_people(soup, company_name, domain, url)
                contacts.extend(found)

                if contacts:
                    break

            except Exception:
                continue

        return contacts

    def _extract_hr_people(self, soup: BeautifulSoup, company_name: str, domain: str, url: str) -> list[HRContact]:
        contacts = []
        text = soup.get_text()

        # Look for structured team member blocks
        # Common patterns: name in h3/h4, title in p/span below
        member_sections = soup.select(
            '[class*="team-member"], [class*="TeamMember"], '
            '[class*="leader"], [class*="person"], '
            '[class*="staff"], [class*="bio"]'
        )

        for section in member_sections:
            section_text = section.get_text().lower()
            is_hr = any(re.search(p, section_text) for p in HR_TITLE_PATTERNS)
            if not is_hr:
                continue

            # Extract name (usually in heading)
            name_el = section.select_one("h2, h3, h4, h5, [class*='name'], strong")
            if not name_el:
                continue

            full_name = name_el.get_text().strip()
            if len(full_name) < 3 or len(full_name) > 60:
                continue

            # Extract title
            title_el = section.select_one("p, span, [class*='title'], [class*='role'], [class*='position']")
            title = title_el.get_text().strip() if title_el else ""

            # Extract email if present
            email = None
            email_link = section.select_one('a[href^="mailto:"]')
            if email_link:
                email = email_link.get("href", "").replace("mailto:", "").strip()

            # Extract LinkedIn
            linkedin = None
            li_link = section.select_one('a[href*="linkedin.com"]')
            if li_link:
                linkedin = li_link.get("href")

            parts = full_name.split()
            if len(parts) >= 2:
                contacts.append(HRContact(
                    company_name=company_name,
                    company_domain=domain,
                    first_name=parts[0],
                    last_name=" ".join(parts[1:]),
                    full_name=full_name,
                    title=title or None,
                    email=email,
                    linkedin_url=linkedin,
                    source="website_team",
                ))

        return contacts
