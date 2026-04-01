import pytest

from dedup import normalize_company_name, merge_companies, deduplicate, _is_valid_company_name
from models import Company


class TestNormalizeCompanyName:
    @pytest.mark.parametrize("raw, expected", [
        ("Acme Corp.", "acme"),
        ("Acme Corporation", "acme"),
        ("Acme Inc.", "acme"),
        ("Acme LLC", "acme"),
        ("  Acme  Holdings ", "acme"),
        ("Acme Technologies", "acme"),
        ("simple", "simple"),
    ])
    def test_strip_suffixes(self, raw: str, expected: str):
        assert normalize_company_name(raw) == expected

    def test_removes_special_chars(self):
        # " Co." suffix is stripped first, then special chars removed
        assert normalize_company_name("O'Brien & Co.") == "obrien"
        assert normalize_company_name("O'Brien & Associates") == "obrien associates"

    def test_collapses_whitespace(self):
        assert normalize_company_name("  Big   Space  Inc ") == "big space"


class TestIsValidCompanyName:
    def test_junk_names_rejected(self):
        assert _is_valid_company_name("chicago") is False
        assert _is_valid_company_name("benefits") is False

    def test_short_names_rejected(self):
        assert _is_valid_company_name("ab") is False

    def test_quoted_names_rejected(self):
        assert _is_valid_company_name('"Some Company"') is False

    def test_colon_names_rejected(self):
        assert _is_valid_company_name("Snippet: some text") is False

    def test_colon_with_llc_allowed(self):
        assert _is_valid_company_name("Colon LLC: legal") is True

    def test_valid_names_accepted(self):
        assert _is_valid_company_name("Acme Corp") is True
        assert _is_valid_company_name("Northern Trust") is True


class TestMergeCompanies:
    def test_merges_sources_and_evidence(self):
        a = Company(name="Acme", sources=["src1"], lnd_evidence=["ev1"], confidence_score=0.5)
        b = Company(name="Acme", sources=["src2"], lnd_evidence=["ev2"], confidence_score=0.8)
        merged = merge_companies(a, b)
        assert set(merged.sources) == {"src1", "src2"}
        assert set(merged.lnd_evidence) == {"ev1", "ev2"}
        assert merged.confidence_score == 0.8

    def test_fills_missing_fields(self):
        a = Company(name="Acme", domain=None, industry="Mfg")
        b = Company(name="Acme", domain="acme.com", industry=None)
        merged = merge_companies(a, b)
        assert merged.domain == "acme.com"
        assert merged.industry == "Mfg"

    def test_keeps_existing_over_new(self):
        a = Company(name="Acme", domain="acme.com")
        b = Company(name="Acme", domain="other.com")
        merged = merge_companies(a, b)
        assert merged.domain == "acme.com"


class TestDeduplicate:
    def test_exact_name_dedup(self):
        companies = [
            Company(name="Acme Inc.", sources=["s1"]),
            Company(name="Acme Inc", sources=["s2"]),
        ]
        result = deduplicate(companies)
        assert len(result) == 1
        assert set(result[0].sources) == {"s1", "s2"}

    def test_domain_dedup(self):
        companies = [
            Company(name="Acme Corp", domain="acme.com", sources=["s1"]),
            Company(name="Acme Inc", domain="www.acme.com", sources=["s2"]),
        ]
        result = deduplicate(companies)
        assert len(result) == 1

    def test_fuzzy_dedup(self):
        companies = [
            Company(name="Northern Trust Corporation", sources=["s1"]),
            Company(name="Northern Trust", sources=["s2"]),
        ]
        result = deduplicate(companies, fuzzy_threshold=80)
        assert len(result) == 1

    def test_different_companies_preserved(self):
        companies = [
            Company(name="Acme Corp"),
            Company(name="Zenith Industries"),
            Company(name="Global Solutions"),
        ]
        result = deduplicate(companies)
        assert len(result) == 3

    def test_junk_names_filtered(self):
        companies = [
            Company(name="Acme Corp"),
            Company(name="chicago"),
            Company(name="ab"),
        ]
        result = deduplicate(companies)
        assert len(result) == 1
        assert result[0].name == "Acme Corp"
