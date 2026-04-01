import json
import logging
import os
from datetime import datetime

import pandas as pd

from models import EnrichedCompany

logger = logging.getLogger(__name__)


def _flatten_results(results: list[EnrichedCompany]) -> list[dict]:
    """Flatten to one row per company-contact pair."""
    rows = []
    for r in results:
        c = r.company
        if r.contacts:
            for contact in r.contacts:
                rows.append({
                    "company_name": c.name,
                    "domain": c.domain or "",
                    "industry": c.industry or "",
                    "employee_count": c.employee_count or "",
                    "has_lnd_budget": c.has_lnd_budget,
                    "lnd_evidence": "; ".join(c.lnd_evidence),
                    "lnd_sources": ", ".join(c.sources),
                    "confidence_score": round(c.confidence_score, 2),
                    "lnd_source_urls": "; ".join(c.lnd_source_urls),
                    "contact_name": contact.full_name or "",
                    "contact_title": contact.title or "",
                    "contact_email": contact.email or "",
                    "contact_email_confidence": round(contact.email_confidence, 2) if contact.email_confidence else "",
                    "contact_linkedin": contact.linkedin_url or "",
                    "contact_phone": contact.phone or "",
                    "contact_source": contact.source or "",
                })
        else:
            rows.append({
                "company_name": c.name,
                "domain": c.domain or "",
                "industry": c.industry or "",
                "employee_count": c.employee_count or "",
                "has_lnd_budget": c.has_lnd_budget,
                "lnd_evidence": "; ".join(c.lnd_evidence),
                "lnd_sources": ", ".join(c.sources),
                "confidence_score": round(c.confidence_score, 2),
                "lnd_source_urls": "; ".join(c.lnd_source_urls),
                "contact_name": "",
                "contact_title": "",
                "contact_email": "",
                "contact_email_confidence": "",
                "contact_linkedin": "",
                "contact_phone": "",
                "contact_source": "",
            })
    return rows


def export_csv(results: list[EnrichedCompany], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    rows = _flatten_results(results)
    df = pd.DataFrame(rows)
    date_str = datetime.now().strftime("%Y%m%d")
    path = os.path.join(output_dir, f"chicago_lnd_companies_{date_str}.csv")
    df.to_csv(path, index=False)
    logger.info(f"Exported {len(rows)} rows to {path}")
    return path


def export_excel(results: list[EnrichedCompany], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    path = os.path.join(output_dir, f"chicago_lnd_companies_{date_str}.xlsx")

    # Sheet 1: Companies (one row per company)
    company_rows = []
    for r in results:
        c = r.company
        company_rows.append({
            "company_name": c.name,
            "domain": c.domain or "",
            "industry": c.industry or "",
            "employee_count": c.employee_count or "",
            "has_lnd_budget": c.has_lnd_budget,
            "lnd_evidence": "; ".join(c.lnd_evidence),
            "lnd_sources": ", ".join(c.sources),
            "confidence_score": round(c.confidence_score, 2),
            "lnd_source_urls": "; ".join(c.lnd_source_urls),
            "num_contacts": len(r.contacts),
        })

    # Sheet 2: Contacts
    contact_rows = []
    for r in results:
        for contact in r.contacts:
            contact_rows.append({
                "company_name": r.company.name,
                "domain": r.company.domain or "",
                "contact_name": contact.full_name or "",
                "contact_title": contact.title or "",
                "contact_email": contact.email or "",
                "contact_email_confidence": round(contact.email_confidence, 2) if contact.email_confidence else "",
                "contact_linkedin": contact.linkedin_url or "",
                "contact_phone": contact.phone or "",
                "contact_source": contact.source or "",
            })

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(company_rows).to_excel(writer, sheet_name="Companies", index=False)
        pd.DataFrame(contact_rows).to_excel(writer, sheet_name="Contacts", index=False)

    logger.info(f"Exported Excel to {path}")
    return path


def export_json(results: list[EnrichedCompany], output_dir: str):
    """Export as JSON for the web UI to consume."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "results.json")
    data = [r.to_dict() for r in results]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Exported JSON to {path}")
    return path
