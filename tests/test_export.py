import json
import os
import pytest

from export import _flatten_results, export_csv, export_json
from models import Company, HRContact, EnrichedCompany


def _make_results() -> list[EnrichedCompany]:
    return [
        EnrichedCompany(
            company=Company(
                name="Acme Corp",
                domain="acme.com",
                has_lnd_budget=True,
                lnd_evidence=["tuition reimbursement"],
                sources=["ddg_search"],
                confidence_score=0.85,
            ),
            contacts=[
                HRContact(
                    company_name="Acme Corp",
                    full_name="Jane Doe",
                    title="HR Director",
                    email="jane@acme.com",
                    email_confidence=0.9,
                    source="apollo",
                ),
            ],
        ),
        EnrichedCompany(
            company=Company(name="Solo Inc", sources=["glassdoor"]),
            contacts=[],
        ),
    ]


class TestFlattenResults:
    def test_contact_row(self):
        rows = _flatten_results(_make_results())
        # 1 contact row + 1 company-only row
        assert len(rows) == 2
        assert rows[0]["contact_name"] == "Jane Doe"
        assert rows[0]["company_name"] == "Acme Corp"

    def test_no_contact_row(self):
        rows = _flatten_results(_make_results())
        assert rows[1]["contact_name"] == ""
        assert rows[1]["company_name"] == "Solo Inc"


class TestExportCSV:
    def test_creates_csv(self, tmp_path):
        results = _make_results()
        path = export_csv(results, str(tmp_path))
        assert os.path.exists(path)
        assert path.endswith(".csv")

        import csv
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["company_name"] == "Acme Corp"


class TestExportJSON:
    def test_creates_json(self, tmp_path):
        results = _make_results()
        path = export_json(results, str(tmp_path))
        assert os.path.exists(path)

        with open(path) as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["company"]["name"] == "Acme Corp"
        assert len(data[0]["contacts"]) == 1
