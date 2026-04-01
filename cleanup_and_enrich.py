#!/usr/bin/env python3
"""
Clean up scraped data, resolve domains (as validation), and enrich.
Uses domain resolution as the key quality signal — if DDG can find
a real company domain for a name, it's a real company.
"""
import json
import logging
import os
import re
import time

from config import CONFIG
from models import Company, EnrichedCompany, HRContact
from dedup import deduplicate
from export import export_csv, export_excel, export_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cleanup")


def is_obviously_not_a_company(name: str) -> bool:
    """Fast check to skip names that are clearly noise."""
    low = name.lower().strip()

    # Too short or too long
    if len(low) < 3 or len(low) > 55:
        return True

    # Starts with a number followed by text (Wikipedia TOC, numbered lists)
    if re.match(r"^\d+\.?\d*\.?\d*\s", low):
        return True

    # Just numbers
    if re.match(r"^[\d\s,.\-+]+$", low):
        return True

    # Contains obvious HTML/page artifacts
    page_artifacts = [
        "subscribe", "newsletter", "cookie", "privacy", "terms of use",
        "ad choice", "advertise", "classified", "reprints", "licensing",
        "contact us", "about us", "join us", "sign up", "log in",
        "download", "e-edition", "manage subscription", "ez pay",
        "vacation stop", "delivery issue", "job board", "job posting",
        "search ", "browse ", "view all", "see more", "read more",
        "learn more", "click here", "get started", "apply now",
        "accessibility", "sitemap", "rss", "podcasts",
        "nomination", "privacy request", "live tv", "schedule",
        "watch", "programs", "donate", "sponsor",
        "membership", "become a member", "renew", "update profile",
        "members only", "bylaws", "constitution", "code of ",
        "mission statement", "board of director", "past president",
        "photo gallery", "calendar", "committee",
        "scholarship", "award program", "recommend",
        "non-", "resources", "materials", "educational",
        "top workplace", "best place", "healthiest",
        "best and brightest", "fortune best",
        "how to", "what is", "why ", "when ",
        "recipe", "dining", "entertainment", "movies", "music",
        "travel", "tv and", "sports", "weather",
        "real estate", "transportation", "immigration",
        "en español", "neighborhoods", "food", "kids",
        "all stocks", "all etfs", "all markets", "all photos",
        "all videos", "all suburbs", "alpha picks",
        "stocks", "etfs", "markets",
        "aerospace", "african american", "hispanic",
        "aboriginal", "native american",
        "pre-european", "prior to statehood", "civil war",
        "topography", "geology", "climate", "urban area",
        "etymology", "hall of fame", "further reading",
        "external links", "references", "personal life",
        "career", "notes", "million",
        "accelerat", "analytics drive",
        "advertis", "advisory", "advocate for",
        "affinity program", "agencies", "agriculture",
        "alternative energ", "alumni", "amusement",
        "assessment development", "adoption",
        "administration", "activities & athletic",
        "bootcamp", "spring conference", "annual meeting",
        "annual luncheon", "pinnacle award",
        "virtual technology", "guide 2026", "guide 2025",
        "atd ", "shrm ", "ishe ", "ashe ", "credo",
        "401k", "401(k",
        "rocketreach", "seekingalpha",
        "checkout", "cart", "wishlist",
        "chatgpt", "gpt", "ai detector", "ai checker",
    ]
    if any(p in low for p in page_artifacts):
        return True

    # No uppercase at all (unlikely company name)
    if not any(c.isupper() for c in name):
        return True

    # More than 7 words (likely a sentence)
    if len(name.split()) > 7:
        return True

    # Looks like a section header (e.g., "Business Business Careers & Finance")
    if len(name) > 40 and name.count(" ") > 4:
        return True

    # URL-like
    if "http" in low or "www." in low or ".com/" in low:
        return True

    return False


# Large enterprises / irrelevant companies to always exclude
EXCLUDE_NAMES = {
    "amazon", "amazon.com", "kaiser permanente", "bank of america",
    "emory healthcare", "molina healthcare", "amn healthcare",
    "loyola university chicago", "loyola", "university of illinois",
    "university of illinois at chicago", "city colleges of chicago",
    "the art institute of chicago", "the art",
    "northwestern university", "rush university", "depaul university",
    "ann & robert h. lurie children's hospital of chicago",
    "northwestern memorial", "advocate aurora", "commonspirit health",
    "ascension", "hca healthcare", "unitedhealth", "humana", "cigna",
    "aetna", "blue cross", "jp morgan", "wells fargo", "citigroup",
    "goldman sachs", "morgan stanley", "state farm", "allstate",
    "walmart", "target", "costco", "kroger", "walgreens", "cvs",
    "home depot", "mcdonalds", "starbucks", "comcast", "at&t",
    "verizon", "ford", "general motors", "ibm", "oracle", "microsoft",
    "google", "apple", "meta", "salesforce", "adobe", "fedex", "ups",
    "arrive logistics", "philadelphia insurance companies",
    "one summer chicago", "kinexon", "centrica", "lensa",
    "join our team", "join the team", "works", "place to work",
    "chart 2024", "empower your career", "cb2",
    "subscription", "download the app", "about crain's",
    "fortune best workplaces in chicago™ 2025 - large",
    "fortune best workplaces in chicago™ 2025 - small and medium",
    "abn amro clearing usa llc", "blackrock",
    "transunion", "helped 5 women in tech grow",
    # BuiltIn companies that are all tech/excluded
    "floqast", "tastytrade", "tastylive", "tastyfx", "tastycrypto",
    "mondelēz international", "mondelez", "occ", "peak6", "avant",
    "velocityehs", "cdw", "coupa", "ninjatrader", "bounteous",
    "supernova technology", "tempus ai", "steelseries",
    "abn amro", "upside",
}


def clean_and_enrich():
    """Load raw data, clean aggressively, resolve domains, enrich, export."""

    # Phase 1: Load all raw scraped data
    raw_dir = CONFIG["raw_dir"]
    all_companies = []
    for filename in os.listdir(raw_dir):
        if filename.endswith(".json") and filename != "merged_companies.json":
            path = os.path.join(raw_dir, filename)
            with open(path) as f:
                data = json.load(f)
            companies = [Company.from_dict(d) for d in data]
            all_companies.extend(companies)
            logger.info(f"Loaded {len(companies)} from {filename}")

    logger.info(f"Total raw companies: {len(all_companies)}")

    # Phase 2: Aggressive noise filtering
    cleaned = []
    for c in all_companies:
        low = c.name.lower().strip()
        if low in EXCLUDE_NAMES:
            continue
        if is_obviously_not_a_company(c.name):
            continue
        cleaned.append(c)

    logger.info(f"After noise filter: {len(cleaned)} companies ({len(all_companies) - len(cleaned)} removed)")

    # Phase 3: Deduplicate
    merged = deduplicate(cleaned, CONFIG["dedup"]["fuzzy_threshold"])
    logger.info(f"After dedup: {len(merged)} companies")

    # Phase 4: Tech/size filtering
    from main import _filter_tech_companies, _filter_by_size, EXCLUDED_COMPANIES
    EXCLUDED_COMPANIES.update(EXCLUDE_NAMES)

    max_emp = CONFIG.get("filters", {}).get("max_employees")
    if max_emp:
        before = len(merged)
        merged = _filter_by_size(merged, max_emp)
        logger.info(f"Size filter: {before} -> {len(merged)}")

    before = len(merged)
    merged = _filter_tech_companies(merged)
    logger.info(f"Tech filter: {before} -> {len(merged)}")

    # Phase 5: Domain resolution — this is our quality gate
    # If DDG can find a domain for the name, it's a real company
    from enrichment.domain_resolver import DomainResolver
    resolver = DomainResolver(CONFIG)

    valid_companies = []
    no_domain_count = 0

    logger.info(f"Resolving domains for {len(merged)} companies (this validates they're real)...")
    for i, c in enumerate(merged):
        if c.domain:
            valid_companies.append(c)
            logger.info(f"  [{i+1}/{len(merged)}] {c.name} -> {c.domain} (existing)")
            continue

        domain = resolver.resolve(c.name)
        if domain:
            c.domain = domain
            valid_companies.append(c)
            logger.info(f"  [{i+1}/{len(merged)}] {c.name} -> {domain}")
        else:
            no_domain_count += 1
            logger.debug(f"  [{i+1}/{len(merged)}] {c.name} -> SKIP (no domain = likely noise)")

    logger.info(f"Domain validation: {len(valid_companies)} real companies, {no_domain_count} dropped")

    # Save cleaned merged data
    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, "merged_companies.json"), "w") as f:
        json.dump([c.to_dict() for c in valid_companies], f, indent=2)

    # Show final company list
    logger.info("=" * 60)
    logger.info("VALIDATED COMPANIES:")
    for c in sorted(valid_companies, key=lambda x: x.name):
        lnd = " [L&D]" if c.has_lnd_budget else ""
        logger.info(f"  {c.name} ({c.domain}){lnd}")
    logger.info("=" * 60)

    # Phase 6: Enrichment
    logger.info(f"Enriching {len(valid_companies)} companies...")

    from enrichment.hunter import HunterEnricher
    from enrichment.website_team import WebsiteTeamEnricher
    from scrapers.ddg_search import DDGContactFinder
    from enrichment.email_guesser import guess_email

    hunter = HunterEnricher(CONFIG)
    website = WebsiteTeamEnricher(CONFIG)
    ddg_contacts = DDGContactFinder()

    results = []
    for i, company in enumerate(valid_companies):
        logger.info(f"Enriching [{i+1}/{len(valid_companies)}]: {company.name} ({company.domain})")
        contacts = []

        # Hunter (verified emails)
        if CONFIG["enrichment"]["hunter"]["enabled"] and company.domain:
            try:
                contacts = hunter.search_hr_contacts(company.name, company.domain)
                if contacts:
                    logger.info(f"  -> Hunter: {len(contacts)} contacts ({sum(1 for c in contacts if c.email)} emails)")
            except Exception as e:
                logger.debug(f"  -> Hunter error: {e}")

        # Website team pages
        if not contacts and CONFIG["enrichment"]["website_team"]["enabled"] and company.domain:
            try:
                contacts = website.search_hr_contacts(company.name, company.domain)
                if contacts:
                    logger.info(f"  -> Website: {len(contacts)} contacts")
            except Exception as e:
                logger.debug(f"  -> Website error: {e}")

        # DDG LinkedIn search
        if not contacts:
            try:
                ddg_results = ddg_contacts.find_hr_contacts(company.name, company.domain)
                if ddg_results:
                    logger.info(f"  -> DDG: {len(ddg_results)} contacts")
                    for dr in ddg_results:
                        contacts.append(HRContact(
                            company_name=company.name,
                            company_domain=company.domain,
                            first_name=dr["first_name"],
                            last_name=dr["last_name"],
                            full_name=dr["full_name"],
                            title=dr.get("title"),
                            linkedin_url=dr.get("linkedin_url"),
                            source="ddg_search",
                        ))
            except Exception as e:
                logger.debug(f"  -> DDG error: {e}")
                time.sleep(5)  # Back off on DDG errors

        # Email enrichment
        if company.domain:
            for c in contacts:
                if not c.email and c.first_name and c.last_name:
                    if hunter.credits_used < hunter.max_credits:
                        try:
                            email = hunter.find_email(company.domain, c.first_name, c.last_name)
                            if email:
                                c.email = email
                                c.email_confidence = 0.85
                                c.source = f"{c.source}+hunter"
                                logger.info(f"    -> Hunter email: {c.full_name}")
                                continue
                        except Exception:
                            pass

                    guessed = guess_email(c.first_name, c.last_name, company.domain)
                    if guessed:
                        c.email = guessed
                        c.email_confidence = 0.6
                        c.source = f"{c.source}+guess"
                        logger.info(f"    -> Guessed email: {guessed}")

        if not contacts:
            logger.info(f"  -> No contacts found")

        results.append(EnrichedCompany(company=company, contacts=contacts))

    # Phase 7: Export
    output_dir = CONFIG["output_dir"]
    export_csv(results, output_dir)
    export_excel(results, output_dir)
    export_json(results, output_dir)

    # Summary
    total = len(results)
    with_contacts = sum(1 for r in results if r.contacts)
    with_email = sum(1 for r in results if any(c.email for c in r.contacts))
    total_contacts = sum(len(r.contacts) for r in results)

    logger.info("=" * 50)
    logger.info(f"DONE! Results saved to {output_dir}/")
    logger.info(f"  Companies: {total}")
    logger.info(f"  With HR contacts: {with_contacts}")
    logger.info(f"  With email: {with_email}")
    logger.info(f"  Total contacts: {total_contacts}")
    logger.info("=" * 50)


if __name__ == "__main__":
    clean_and_enrich()
