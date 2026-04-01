import pytest

from models import Company, HRContact, EnrichedCompany


class TestCompany:
    def test_defaults(self):
        c = Company(name="Acme Corp")
        assert c.name == "Acme Corp"
        assert c.headquarters_city == "Chicago"
        assert c.has_lnd_budget is False
        assert c.sources == []
        assert c.confidence_score == 0.0

    def test_to_dict_roundtrip(self):
        c = Company(
            name="Acme Corp",
            domain="acme.com",
            industry="Manufacturing",
            employee_count="200",
            has_lnd_budget=True,
            lnd_evidence=["tuition reimbursement"],
            sources=["ddg_search"],
            confidence_score=0.8,
        )
        d = c.to_dict()
        assert d["name"] == "Acme Corp"
        assert d["domain"] == "acme.com"
        assert d["has_lnd_budget"] is True

        c2 = Company.from_dict(d)
        assert c2.name == c.name
        assert c2.domain == c.domain
        assert c2.lnd_evidence == c.lnd_evidence

    def test_from_dict_ignores_extra_keys(self):
        d = {"name": "Test", "unknown_field": "ignored"}
        c = Company.from_dict(d)
        assert c.name == "Test"


class TestHRContact:
    def test_defaults(self):
        contact = HRContact(company_name="Acme Corp")
        assert contact.email is None
        assert contact.source is None

    def test_to_dict_roundtrip(self):
        contact = HRContact(
            company_name="Acme Corp",
            first_name="Jane",
            last_name="Doe",
            full_name="Jane Doe",
            title="HR Director",
            email="jane.doe@acme.com",
            email_confidence=0.95,
            source="apollo",
        )
        d = contact.to_dict()
        c2 = HRContact.from_dict(d)
        assert c2.full_name == "Jane Doe"
        assert c2.email_confidence == 0.95
        assert c2.source == "apollo"


class TestEnrichedCompany:
    def test_to_dict_roundtrip(self):
        ec = EnrichedCompany(
            company=Company(name="Acme Corp", domain="acme.com"),
            contacts=[
                HRContact(company_name="Acme Corp", full_name="Jane Doe", source="hunter"),
            ],
        )
        d = ec.to_dict()
        assert d["company"]["name"] == "Acme Corp"
        assert len(d["contacts"]) == 1

        ec2 = EnrichedCompany.from_dict(d)
        assert ec2.company.name == "Acme Corp"
        assert ec2.contacts[0].full_name == "Jane Doe"

    def test_empty_contacts(self):
        ec = EnrichedCompany(company=Company(name="Solo"))
        d = ec.to_dict()
        assert d["contacts"] == []

        ec2 = EnrichedCompany.from_dict(d)
        assert ec2.contacts == []
