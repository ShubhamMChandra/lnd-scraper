from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Company:
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    headquarters_city: str = "Chicago"
    address: Optional[str] = None

    has_lnd_budget: bool = False
    lnd_evidence: list[str] = field(default_factory=list)
    lnd_source_urls: list[str] = field(default_factory=list)
    benefits_summary: Optional[str] = None

    sources: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    normalized_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "industry": self.industry,
            "employee_count": self.employee_count,
            "headquarters_city": self.headquarters_city,
            "address": self.address,
            "has_lnd_budget": self.has_lnd_budget,
            "lnd_evidence": self.lnd_evidence,
            "lnd_source_urls": self.lnd_source_urls,
            "benefits_summary": self.benefits_summary,
            "sources": self.sources,
            "confidence_score": self.confidence_score,
            "last_updated": self.last_updated,
            "normalized_name": self.normalized_name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Company":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class HRContact:
    company_name: str
    company_domain: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    email_confidence: Optional[float] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "title": self.title,
            "email": self.email,
            "email_confidence": self.email_confidence,
            "linkedin_url": self.linkedin_url,
            "phone": self.phone,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HRContact":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EnrichedCompany:
    company: Company
    contacts: list[HRContact] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "company": self.company.to_dict(),
            "contacts": [c.to_dict() for c in self.contacts],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EnrichedCompany":
        return cls(
            company=Company.from_dict(d["company"]),
            contacts=[HRContact.from_dict(c) for c in d.get("contacts", [])],
        )
