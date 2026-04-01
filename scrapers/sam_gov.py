"""
SAM.gov federal contractor scraper.

Uses the SAM.gov Entity Management API (public DEMO_KEY) to find
Chicago-area federal contractors in traditional industries.
Federal contractors often have mandated training/compliance programs,
making them likely L&D budget holders.

ICP: middle-market (50-750 employees), traditional industries in Chicago.
NOT tech/AI/SaaS.
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from models import Company
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# SAM.gov Entity Management API
SAM_API_BASE = "https://api.sam.gov/entity-information/v3/entities"
SAM_API_KEY = "DEMO_KEY"

# Target NAICS prefixes mapped to human-readable industry names.
# These cover traditional, non-tech industries likely to have L&D budgets.
TARGET_NAICS = {
    "621": "Healthcare (Ambulatory)",
    "622": "Hospitals",
    "623": "Nursing & Residential Care",
    "236": "Construction (Building)",
    "237": "Construction (Heavy/Civil)",
    "238": "Construction (Specialty Trade)",
    "311": "Manufacturing (Food)",
    "312": "Manufacturing (Beverage/Tobacco)",
    "313": "Manufacturing (Textile)",
    "314": "Manufacturing (Textile Products)",
    "315": "Manufacturing (Apparel)",
    "316": "Manufacturing (Leather)",
    "321": "Manufacturing (Wood)",
    "322": "Manufacturing (Paper)",
    "323": "Manufacturing (Printing)",
    "324": "Manufacturing (Petroleum/Coal)",
    "325": "Manufacturing (Chemical)",
    "326": "Manufacturing (Plastics/Rubber)",
    "327": "Manufacturing (Nonmetallic Mineral)",
    "331": "Manufacturing (Primary Metal)",
    "332": "Manufacturing (Fabricated Metal)",
    "333": "Manufacturing (Machinery)",
    "334": "Manufacturing (Computer/Electronic)",
    "335": "Manufacturing (Electrical Equipment)",
    "336": "Manufacturing (Transportation Equipment)",
    "337": "Manufacturing (Furniture)",
    "339": "Manufacturing (Miscellaneous)",
    "522": "Financial Services (Credit/Lending)",
    "523": "Financial Services (Securities/Investments)",
    "524": "Insurance",
    "531": "Real Estate",
    "484": "Transportation (Trucking)",
    "488": "Transportation (Support Activities)",
    "493": "Warehousing & Storage",
    "541211": "Offices of CPAs",
    "541110": "Law Firms",
    "813": "Nonprofits & Membership Organizations",
}

# NAICS prefixes that indicate tech/SaaS -- skip these entities
TECH_NAICS_PREFIXES = ("5112", "5182", "5191", "5415")


def _extract_domain(url: Optional[str]) -> Optional[str]:
    """Extract a clean domain from a URL string."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


def _normalize_name(name: str) -> str:
    """Normalize a business name for dedup comparison."""
    name = name.strip().title()
    # Strip common suffixes for comparison key only
    suffixes = r",?\s*(Inc\.?|LLC|Corp\.?|Co\.?|Ltd\.?|L\.?P\.?|LLP|PC|P\.C\.)$"
    return re.sub(suffixes, "", name, flags=re.IGNORECASE).strip()


class SAMGovScraper(BaseScraper):
    """
    Scrapes SAM.gov Entity Management API for active federal contractors
    headquartered in Chicago across target NAICS industries.
    """

    name = "sam_gov"
    rate_limit_seconds = 3.0

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = self.config.get("sam_gov_api_key", SAM_API_KEY)
        self.max_records_per_naics = self.config.get("sam_gov_max_per_naics", 100)

    def _build_params(self, naics_code: str, page: int = 0) -> dict:
        """Build query parameters for the SAM.gov API."""
        return {
            "api_key": self.api_key,
            "stateCode": "IL",
            "city": "CHICAGO",
            "registrationStatus": "A",
            "naicsAnySize": naics_code,
            "includeSections": "entityRegistration,coreData",
            "page": page,
            "size": 100,
        }

    def _parse_entity(self, entity: dict) -> Optional[Company]:
        """Parse a single SAM.gov entity record into a Company."""
        try:
            registration = entity.get("entityRegistration", {})
            core_data = entity.get("coreData", {})

            legal_name = registration.get("legalBusinessName", "")
            if not legal_name:
                return None

            # Skip very short or generic names
            if len(legal_name.strip()) < 3:
                return None

            # Build address from physical address data
            phys_addr = core_data.get("physicalAddress", {})
            address_parts = []
            if phys_addr.get("addressLine1"):
                address_parts.append(phys_addr["addressLine1"])
            if phys_addr.get("city"):
                address_parts.append(phys_addr["city"])
            if phys_addr.get("stateOrProvinceCode"):
                address_parts.append(phys_addr["stateOrProvinceCode"])
            if phys_addr.get("zipCode"):
                address_parts.append(phys_addr["zipCode"])
            address = ", ".join(address_parts) if address_parts else None

            # Extract website/domain from entity data
            entity_info = core_data.get("entityInformation", {})
            website = entity_info.get("entityURL") or entity_info.get("entityWebsite")
            domain = _extract_domain(website)

            # Determine industry from NAICS
            naics_list = core_data.get("naicsList", [])
            industry = None
            is_tech = False
            for naics_entry in naics_list:
                code = str(naics_entry.get("naicsCode", ""))
                # Check if this is a tech company
                if any(code.startswith(tp) for tp in TECH_NAICS_PREFIXES):
                    is_tech = True
                    break
                # Match to our target industries
                if not industry:
                    for prefix, ind_name in TARGET_NAICS.items():
                        if code.startswith(prefix):
                            industry = ind_name
                            break

            if is_tech:
                return None

            # Attempt to get primary NAICS description as fallback industry
            if not industry and naics_list:
                primary = next(
                    (n for n in naics_list if n.get("isPrimary")),
                    naics_list[0] if naics_list else None,
                )
                if primary:
                    industry = primary.get("naicsCodeDescription", None)

            name = _normalize_name(legal_name)

            return Company(
                name=name,
                domain=domain,
                industry=industry,
                headquarters_city="Chicago",
                address=address,
                has_lnd_budget=False,
                lnd_evidence=[
                    "Federal contractor - likely has training/compliance programs"
                ],
                lnd_source_urls=[
                    f"https://sam.gov/entity/{registration.get('ueiSAM', '')}"
                ],
                sources=["sam_gov"],
                confidence_score=0.3,
            )
        except Exception as e:
            self.logger.warning(f"Error parsing SAM.gov entity: {e}")
            return None

    def _fetch_naics(self, naics_code: str, industry_label: str) -> list[Company]:
        """Fetch all entities for a given NAICS code from SAM.gov."""
        companies = []
        page = 0

        while len(companies) < self.max_records_per_naics:
            params = self._build_params(naics_code, page=page)
            try:
                resp = self._request(SAM_API_BASE, params=params)
                if resp.status_code != 200:
                    self.logger.warning(
                        f"SAM.gov returned {resp.status_code} for NAICS {naics_code}"
                    )
                    break

                data = resp.json()
            except Exception as e:
                self.logger.error(
                    f"SAM.gov request failed for NAICS {naics_code}: {e}"
                )
                break

            entities = data.get("entityData", [])
            if not entities:
                break

            for entity in entities:
                company = self._parse_entity(entity)
                if company:
                    # Set industry from our mapping if parse didn't find one
                    if not company.industry:
                        company.industry = industry_label
                    companies.append(company)

            total = data.get("totalRecords", 0)
            fetched = (page + 1) * 100
            if fetched >= total or fetched >= self.max_records_per_naics:
                break

            page += 1

        return companies

    def scrape(self) -> list[Company]:
        """
        Query SAM.gov for each target NAICS prefix, collect Chicago-area
        federal contractors, deduplicate, and return Company list.
        """
        all_companies: dict[str, Company] = {}
        total_naics = len(TARGET_NAICS)

        for idx, (naics_code, industry_label) in enumerate(TARGET_NAICS.items(), 1):
            self.logger.info(
                f"[{idx}/{total_naics}] Querying SAM.gov for NAICS {naics_code} "
                f"({industry_label})..."
            )

            try:
                batch = self._fetch_naics(naics_code, industry_label)
            except Exception as e:
                self.logger.error(
                    f"Unexpected error for NAICS {naics_code}: {e}"
                )
                continue

            for company in batch:
                # Deduplicate by normalized lowercase name
                key = company.name.lower().strip()
                if key in all_companies:
                    existing = all_companies[key]
                    # Merge evidence and source URLs
                    for ev in company.lnd_evidence:
                        if ev not in existing.lnd_evidence:
                            existing.lnd_evidence.append(ev)
                    for url in company.lnd_source_urls:
                        if url not in existing.lnd_source_urls:
                            existing.lnd_source_urls.append(url)
                    # Keep the domain if existing doesn't have one
                    if not existing.domain and company.domain:
                        existing.domain = company.domain
                    # Keep the address if existing doesn't have one
                    if not existing.address and company.address:
                        existing.address = company.address
                else:
                    all_companies[key] = company

            self.logger.info(
                f"  Found {len(batch)} entities, "
                f"{len(all_companies)} unique total so far"
            )

        companies = list(all_companies.values())
        self.logger.info(
            f"SAM.gov scraper complete: {len(companies)} unique companies found"
        )

        self.save_raw(companies)
        return companies
