import logging
import time
from typing import Optional

import requests

from models import HRContact

logger = logging.getLogger(__name__)

HR_TITLES = [
    "HR Director", "VP People", "VP Human Resources",
    "Chief People Officer", "Head of People", "Head of HR",
    "Director of Human Resources", "HR Manager",
    "People Operations Manager", "People Operations Director",
    "Director of Learning and Development",
    "Director of Talent Development",
    "Learning & Development Manager",
    "Talent Development Manager",
    "Director of People Operations",
    "Senior HR Manager",
    "VP of People",
    "VP of Talent",
    "Chief Learning Officer",
]


class ApolloEnricher:
    def __init__(self, config: dict):
        self.api_key = config.get("apollo_api_key")
        self.credits_used = 0
        self.max_credits = config.get("enrichment", {}).get("apollo", {}).get("max_credits", 2000)
        self.logger = logging.getLogger("enrichment.apollo")
        self._api_accessible = True  # Will be set False if free plan blocks us

    def search_and_enrich(self, company_name: str, domain: Optional[str]) -> list[HRContact]:
        if not self.api_key or not self._api_accessible:
            return []

        contacts = []

        # Try people/search endpoint (available on some free plans)
        people = self._search_people(company_name, domain)

        for person in people[:2]:
            if self.credits_used >= self.max_credits:
                self.logger.warning("Apollo credit budget exhausted")
                break

            contact = self._person_to_contact(person, company_name, domain)
            if contact:
                contacts.append(contact)

        # If search worked but no emails, try people/match for enrichment
        if people and not any(c.email for c in contacts):
            for person in people[:2]:
                enriched = self._enrich_person(person, company_name, domain)
                if enriched and enriched.email:
                    # Update existing contact or add new
                    found = False
                    for c in contacts:
                        if c.full_name == enriched.full_name:
                            c.email = enriched.email
                            c.email_confidence = enriched.email_confidence
                            found = True
                            break
                    if not found:
                        contacts.append(enriched)

        return contacts

    def _search_people(self, company_name: str, domain: Optional[str]) -> list[dict]:
        """Search for HR contacts at a company."""
        # Try multiple endpoints in order of free-tier accessibility
        endpoints = [
            "https://api.apollo.io/v1/mixed_people/search",
            "https://api.apollo.io/api/v1/mixed_people/search",
        ]

        body = {
            "person_titles": HR_TITLES,
            "per_page": 5,
        }
        if domain:
            body["organization_domains"] = [domain]
        else:
            body["q_organization_name"] = company_name

        for endpoint in endpoints:
            try:
                resp = requests.post(
                    endpoint,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=30,
                )

                if resp.status_code == 403:
                    self.logger.debug(f"Apollo endpoint blocked on free plan: {endpoint}")
                    continue

                if resp.status_code == 429:
                    self.logger.warning("Apollo rate limited, waiting 30s")
                    time.sleep(30)
                    return []

                if resp.status_code == 200:
                    data = resp.json()
                    people = data.get("people", [])
                    self.logger.debug(f"Apollo found {len(people)} people for {company_name}")
                    return people

                self.logger.debug(f"Apollo search {resp.status_code} for {company_name}: {resp.text[:200]}")

            except Exception as e:
                self.logger.error(f"Apollo search error for {company_name}: {e}")

        # If all endpoints fail with 403, mark API as inaccessible
        self._api_accessible = False
        self.logger.info("Apollo API not accessible on free plan, disabling")
        return []

    def _person_to_contact(self, person: dict, company_name: str, domain: Optional[str]) -> Optional[HRContact]:
        """Convert Apollo person dict to HRContact without extra API call."""
        first_name = person.get("first_name", "")
        last_name = person.get("last_name", "")
        if not first_name or not last_name:
            return None

        email = person.get("email")
        linkedin = person.get("linkedin_url")
        title = person.get("title", "")

        return HRContact(
            company_name=company_name,
            company_domain=domain,
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}",
            title=title,
            email=email,
            email_confidence=0.9 if email else None,
            linkedin_url=linkedin,
            source="apollo",
        )

    def _enrich_person(self, person: dict, company_name: str, domain: Optional[str]) -> Optional[HRContact]:
        """Enrich a person to get their email. Costs 1 credit."""
        first_name = person.get("first_name", "")
        last_name = person.get("last_name", "")
        if not first_name or not last_name:
            return None

        try:
            body = {
                "first_name": first_name,
                "last_name": last_name,
                "organization_name": company_name,
            }
            if domain:
                body["domain"] = domain

            resp = requests.post(
                "https://api.apollo.io/api/v1/people/match",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=30,
            )

            self.credits_used += 1

            if resp.status_code != 200:
                self.logger.debug(f"Apollo enrich {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            person_data = data.get("person", {})
            if not person_data:
                return None

            email = person_data.get("email")
            linkedin = person_data.get("linkedin_url")
            title = person_data.get("title", person.get("title", ""))
            phone_numbers = person_data.get("phone_numbers", [])
            phone = phone_numbers[0].get("sanitized_number") if phone_numbers else None

            return HRContact(
                company_name=company_name,
                company_domain=domain,
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}",
                title=title,
                email=email,
                email_confidence=0.9 if email else None,
                linkedin_url=linkedin,
                phone=phone,
                source="apollo",
            )

        except Exception as e:
            self.logger.error(f"Apollo enrich error: {e}")
            return None

        finally:
            time.sleep(1)
