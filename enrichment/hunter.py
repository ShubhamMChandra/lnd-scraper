import logging
import time
from typing import Optional

import requests

from models import HRContact

logger = logging.getLogger(__name__)


class HunterEnricher:
    def __init__(self, config: dict):
        self.api_key = config.get("hunter_api_key")
        self.credits_used = 0
        self.max_credits = config.get("enrichment", {}).get("hunter", {}).get("max_credits", 50)
        self.logger = logging.getLogger("enrichment.hunter")

    def search_hr_contacts(self, company_name: str, domain: Optional[str]) -> list[HRContact]:
        if not self.api_key or not domain:
            return []

        if self.credits_used >= self.max_credits:
            self.logger.debug("Hunter credit budget exhausted")
            return []

        contacts = []
        try:
            resp = requests.get(
                "https://api.hunter.io/v2/domain-search",
                params={
                    "domain": domain,
                    "api_key": self.api_key,
                    "limit": 10,
                },
                timeout=30,
            )

            self.credits_used += 1

            if resp.status_code != 200:
                self.logger.debug(f"Hunter returned {resp.status_code} for {domain}")
                return []

            data = resp.json()
            emails = data.get("data", {}).get("emails", [])

            for email_data in emails[:3]:
                email = email_data.get("value")
                first_name = email_data.get("first_name", "")
                last_name = email_data.get("last_name", "")
                position = email_data.get("position", "")
                confidence = email_data.get("confidence", 0)
                linkedin = email_data.get("linkedin")

                # Include if it looks like an HR contact by title or department
                department = email_data.get("department", "")
                hr_keywords = [
                    "hr", "human resource", "people", "talent",
                    "learning", "development", "training", "recruit",
                ]
                combined = f"{position} {department}".lower()
                if any(kw in combined for kw in hr_keywords):
                    contacts.append(HRContact(
                        company_name=company_name,
                        company_domain=domain,
                        first_name=first_name or None,
                        last_name=last_name or None,
                        full_name=f"{first_name} {last_name}".strip() or None,
                        title=position or None,
                        email=email,
                        email_confidence=confidence / 100.0 if confidence else None,
                        linkedin_url=linkedin,
                        source="hunter",
                    ))

        except Exception as e:
            self.logger.error(f"Hunter error for {domain}: {e}")

        time.sleep(1)
        return contacts

    def find_email(self, domain: str, first_name: str, last_name: str) -> Optional[str]:
        """Find email for a specific person. Costs 1 credit."""
        if not self.api_key or self.credits_used >= self.max_credits:
            return None

        try:
            resp = requests.get(
                "https://api.hunter.io/v2/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": self.api_key,
                },
                timeout=30,
            )
            self.credits_used += 1

            if resp.status_code != 200:
                return None

            data = resp.json()
            email = data.get("data", {}).get("email")
            return email

        except Exception as e:
            self.logger.error(f"Hunter email finder error: {e}")
            return None
