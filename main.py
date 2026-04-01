#!/usr/bin/env python3
"""
Chicago L&D Budget Company Scraper
Finds Chicago companies offering Learning & Development budgets,
enriches with HR contact information, and serves a local web UI.
"""
import argparse
import json
import logging
import os
import sys

from config import CONFIG
from models import Company, EnrichedCompany
from dedup import deduplicate
from export import export_csv, export_excel, export_json

logger = logging.getLogger("main")


def run_scrapers(limit: int = None) -> list[Company]:
    """Phase 1: Run all scrapers to identify companies."""
    from scrapers.serpapi_google import SerpAPIGoogleScraper
    from scrapers.serpapi_jobs import SerpAPIJobsScraper
    from scrapers.glassdoor import GlassdoorScraper
    from scrapers.builtin_chicago import BuiltInChicagoScraper
    from scrapers.crains import CrainsScraper
    from scrapers.greatplacetowork import GreatPlaceToWorkScraper

    scrapers = [
        SerpAPIGoogleScraper(CONFIG),
        SerpAPIJobsScraper(CONFIG),
        GlassdoorScraper(CONFIG),
        BuiltInChicagoScraper(CONFIG),
        CrainsScraper(CONFIG),
        GreatPlaceToWorkScraper(CONFIG),
    ]

    all_companies = []
    for scraper in scrapers:
        scraper_config = CONFIG["scrapers"].get(scraper.name, {})
        if not scraper_config.get("enabled", True):
            logger.info(f"Skipping disabled scraper: {scraper.name}")
            continue

        logger.info(f"Running scraper: {scraper.name}")
        try:
            companies = scraper.scrape()
            scraper.save_raw(companies)
            all_companies.extend(companies)
            logger.info(f"  -> {len(companies)} companies found")
        except Exception as e:
            logger.error(f"  -> Scraper {scraper.name} failed: {e}")

    # Deduplicate
    logger.info(f"Total raw companies: {len(all_companies)}")
    merged = deduplicate(all_companies, CONFIG["dedup"]["fuzzy_threshold"])

    # Confirm L&D via career pages for unconfirmed companies
    from scrapers.career_pages import CareerPagesScraper
    career_scraper = CareerPagesScraper(CONFIG)

    unconfirmed = [c for c in merged if not c.has_lnd_budget and c.domain]
    logger.info(f"Checking {len(unconfirmed)} unconfirmed companies via career pages")
    for c in unconfirmed:
        evidence = career_scraper.check_lnd(c.domain)
        if evidence:
            c.has_lnd_budget = True
            c.lnd_evidence.extend(evidence)
            c.sources.append("career_page")
            c.confidence_score = max(c.confidence_score, 0.7)

    confirmed = [c for c in merged if c.has_lnd_budget]
    logger.info(f"Confirmed L&D companies: {len(confirmed)} / {len(merged)} total")

    # Resolve domains for companies that don't have them
    from enrichment.domain_resolver import DomainResolver
    resolver = DomainResolver(CONFIG)
    no_domain = [c for c in confirmed if not c.domain]
    logger.info(f"Resolving domains for {len(no_domain)} companies...")
    for c in no_domain:
        domain = resolver.resolve(c.name)
        if domain:
            c.domain = domain
            logger.debug(f"  {c.name} -> {domain}")
    with_domain = sum(1 for c in confirmed if c.domain)
    logger.info(f"Domain resolution: {with_domain}/{len(confirmed)} companies have domains")

    if limit:
        confirmed = confirmed[:limit]

    # Save merged results
    raw_dir = CONFIG["raw_dir"]
    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, "merged_companies.json"), "w") as f:
        json.dump([c.to_dict() for c in merged], f, indent=2)

    return confirmed


def run_enrichment(companies: list[Company]) -> list[EnrichedCompany]:
    """Phase 2: Enrich companies with HR contact info."""
    from enrichment.apollo import ApolloEnricher
    from enrichment.hunter import HunterEnricher
    from enrichment.google_search import GoogleSearchEnricher
    from enrichment.website_team import WebsiteTeamEnricher

    apollo = ApolloEnricher(CONFIG)
    hunter = HunterEnricher(CONFIG)
    google = GoogleSearchEnricher(CONFIG)
    website = WebsiteTeamEnricher(CONFIG)

    results = []
    for i, company in enumerate(companies):
        logger.info(f"Enriching [{i+1}/{len(companies)}]: {company.name}")
        contacts = []

        # Try Hunter first (returns actual emails)
        if not contacts and CONFIG["enrichment"]["hunter"]["enabled"] and company.domain:
            contacts = hunter.search_hr_contacts(company.name, company.domain)
            if contacts:
                logger.info(f"  -> Hunter: {len(contacts)} contacts ({sum(1 for c in contacts if c.email)} with email)")

        # Try Apollo
        if not contacts and CONFIG["enrichment"]["apollo"]["enabled"]:
            contacts = apollo.search_and_enrich(company.name, company.domain)
            if contacts:
                logger.info(f"  -> Apollo: {len(contacts)} contacts ({sum(1 for c in contacts if c.email)} with email)")

        # Try Google search for LinkedIn profiles
        if not contacts and CONFIG["enrichment"]["google_search"]["enabled"]:
            google_contacts = google.search_hr_contacts(company.name, company.domain)
            if google_contacts:
                logger.info(f"  -> Google: {len(google_contacts)} contacts (LinkedIn profiles)")
                # Try to get emails for Google-found contacts via Hunter email finder
                if CONFIG["enrichment"]["hunter"]["enabled"] and company.domain and hunter.credits_used < hunter.max_credits:
                    for gc in google_contacts:
                        if gc.first_name and gc.last_name:
                            email = hunter.find_email(company.domain, gc.first_name, gc.last_name)
                            if email:
                                gc.email = email
                                gc.email_confidence = 0.8
                                gc.source = "google_search+hunter"
                                logger.info(f"    -> Found email for {gc.full_name} via Hunter")
                contacts = google_contacts

        # Try website team pages
        if not contacts and CONFIG["enrichment"]["website_team"]["enabled"]:
            contacts = website.search_hr_contacts(company.name, company.domain)
            if contacts:
                logger.info(f"  -> Website: {len(contacts)} contacts")

        if not contacts:
            logger.info(f"  -> No contacts found")

        results.append(EnrichedCompany(company=company, contacts=contacts))

    return results


def load_cached_companies() -> list[Company]:
    """Load previously scraped companies from raw data."""
    path = os.path.join(CONFIG["raw_dir"], "merged_companies.json")
    if not os.path.exists(path):
        logger.error(f"No cached data found at {path}. Run --scrape-only first.")
        return []

    with open(path) as f:
        data = json.load(f)

    companies = [Company.from_dict(d) for d in data]
    confirmed = [c for c in companies if c.has_lnd_budget]
    logger.info(f"Loaded {len(confirmed)} confirmed companies from cache")
    return confirmed


def load_cached_results() -> list[EnrichedCompany]:
    """Load previously exported results."""
    path = os.path.join(CONFIG["output_dir"], "results.json")
    if not os.path.exists(path):
        logger.error(f"No results found at {path}. Run the full pipeline first.")
        return []

    with open(path) as f:
        data = json.load(f)

    return [EnrichedCompany.from_dict(d) for d in data]


def run_ui():
    """Launch the Flask web UI."""
    from web.app import create_app
    app = create_app()
    logger.info("Starting web UI at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)


def main():
    parser = argparse.ArgumentParser(description="Chicago L&D Company Scraper")
    parser.add_argument("--scrape-only", action="store_true", help="Only run scrapers (Phase 1)")
    parser.add_argument("--enrich-only", action="store_true", help="Only run enrichment (Phase 2), uses cached scrape data")
    parser.add_argument("--ui", action="store_true", help="Launch web UI only")
    parser.add_argument("--limit", type=int, help="Limit number of companies to process")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose/debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.ui:
        run_ui()
        return

    if args.enrich_only:
        companies = load_cached_companies()
        if not companies:
            return
        if args.limit:
            companies = companies[:args.limit]
    elif args.scrape_only:
        companies = run_scrapers(limit=args.limit)
        logger.info(f"Scraping complete. {len(companies)} confirmed L&D companies saved.")
        return
    else:
        companies = run_scrapers(limit=args.limit)

    if not companies:
        logger.warning("No companies found. Check API keys and try again.")
        return

    # Phase 2: Enrich
    results = run_enrichment(companies)

    # Phase 3: Export
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
    logger.info("Run with --ui to browse results in your browser")


if __name__ == "__main__":
    main()
