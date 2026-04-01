import re
import logging
from typing import Optional

from thefuzz import fuzz

from models import Company

logger = logging.getLogger(__name__)

SUFFIXES = [
    " incorporated", " inc.", " inc", " llc", " l.l.c.", " corp.", " corp",
    " corporation", " co.", " ltd.", " ltd", " holdings", " group",
    " technologies", " technology", " solutions", " services",
    " consulting", " partners", " worldwide", " global", " international",
]


def normalize_company_name(name: str) -> str:
    name = name.lower().strip()
    for suffix in SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def merge_companies(existing: Company, new: Company) -> Company:
    existing.sources = list(set(existing.sources + new.sources))
    existing.lnd_evidence = list(set(existing.lnd_evidence + new.lnd_evidence))
    existing.lnd_source_urls = list(set(existing.lnd_source_urls + new.lnd_source_urls))
    existing.domain = existing.domain or new.domain
    existing.industry = existing.industry or new.industry
    existing.employee_count = existing.employee_count or new.employee_count
    existing.address = existing.address or new.address
    existing.benefits_summary = existing.benefits_summary or new.benefits_summary
    existing.confidence_score = max(existing.confidence_score, new.confidence_score)
    existing.has_lnd_budget = existing.has_lnd_budget or new.has_lnd_budget
    return existing


JUNK_NAMES = {
    "chicago", "we offer", "work", "employee", "company", "employer",
    "budget", "benefit", "benefits", "training", "development",
    "the", "a", "an", "perk", "review",
}


def _is_valid_company_name(name: str) -> bool:
    """Filter obviously bad company names."""
    norm = name.lower().strip()
    if norm in JUNK_NAMES:
        return False
    if len(norm) < 3:
        return False
    if '"' in name:
        return False
    # Names with colons usually indicate snippet fragments
    if ":" in name and "LLC" not in name:
        return False
    # Names that are just common words
    if re.match(r"^(the|a|an)\s+\w+$", norm):
        return False
    return True


def deduplicate(companies: list[Company], fuzzy_threshold: int = 85) -> list[Company]:
    """Deduplicate companies by normalized name, domain, and fuzzy matching."""
    # Filter invalid names first
    companies = [c for c in companies if _is_valid_company_name(c.name)]

    # Normalize all names
    for c in companies:
        c.normalized_name = normalize_company_name(c.name)

    # Phase 1: Group by domain
    domain_groups: dict[str, Company] = {}
    no_domain: list[Company] = []

    for c in companies:
        if c.domain:
            domain_key = c.domain.lower().replace("www.", "")
            if domain_key in domain_groups:
                domain_groups[domain_key] = merge_companies(domain_groups[domain_key], c)
            else:
                domain_groups[domain_key] = c
        else:
            no_domain.append(c)

    # Phase 2: Group by exact normalized name
    name_groups: dict[str, Company] = {}
    for c in list(domain_groups.values()):
        if c.normalized_name in name_groups:
            name_groups[c.normalized_name] = merge_companies(name_groups[c.normalized_name], c)
        else:
            name_groups[c.normalized_name] = c

    remaining: list[Company] = []
    for c in no_domain:
        if c.normalized_name in name_groups:
            name_groups[c.normalized_name] = merge_companies(name_groups[c.normalized_name], c)
        else:
            remaining.append(c)

    # Phase 3: Fuzzy match remaining against known
    merged = list(name_groups.values())
    for c in remaining:
        matched = False
        for existing in merged:
            score = fuzz.token_sort_ratio(c.normalized_name, existing.normalized_name)
            if score >= fuzzy_threshold:
                merge_companies(existing, c)
                matched = True
                break
        if not matched:
            merged.append(c)

    logger.info(f"Dedup: {len(companies)} -> {len(merged)} companies")
    return merged


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    print("dedup.py is a library module. Import and call deduplicate() from your code.")
    sys.exit(1)
