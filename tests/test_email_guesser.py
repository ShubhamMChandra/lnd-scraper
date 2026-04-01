import pytest
from unittest.mock import patch, MagicMock

from enrichment.email_guesser import _generate_patterns, guess_email


class TestGeneratePatterns:
    def test_standard_patterns(self):
        patterns = _generate_patterns("Jane", "Doe", "acme.com")
        assert "jane.doe@acme.com" in patterns
        assert "janedoe@acme.com" in patterns
        assert "jdoe@acme.com" in patterns
        assert "jane@acme.com" in patterns
        assert "jane_doe@acme.com" in patterns
        assert "j.doe@acme.com" in patterns
        assert "doej@acme.com" in patterns
        assert "doe.jane@acme.com" in patterns
        assert "doe@acme.com" in patterns

    def test_pattern_count(self):
        patterns = _generate_patterns("John", "Smith", "example.com")
        assert len(patterns) == 11

    def test_lowercases(self):
        patterns = _generate_patterns("JOHN", "SMITH", "Example.com")
        assert all("@Example.com" in p for p in patterns)
        # Local parts should be lowercase
        for p in patterns:
            local = p.split("@")[0]
            assert local == local.lower()


class TestGuessEmail:
    def test_returns_none_for_missing_inputs(self):
        assert guess_email("", "Doe", "acme.com") is None
        assert guess_email("Jane", "", "acme.com") is None
        assert guess_email("Jane", "Doe", "") is None

    @patch("enrichment.email_guesser._get_mx_host", return_value=None)
    def test_returns_best_guess_when_no_mx(self, mock_mx):
        # Clear caches for test isolation
        import enrichment.email_guesser as eg
        eg._mx_cache.clear()

        result = guess_email("Jane", "Doe", "nomx.com")
        assert result == "jane.doe@nomx.com"

    @patch("enrichment.email_guesser._verify_email_smtp", return_value=False)
    @patch("enrichment.email_guesser._get_mx_host", return_value="mx.acme.com")
    @patch("enrichment.email_guesser._is_catchall", return_value=True)
    def test_returns_best_guess_for_catchall(self, mock_catchall, mock_mx, mock_verify):
        import enrichment.email_guesser as eg
        eg._mx_cache.clear()

        result = guess_email("Jane", "Doe", "catchall.com")
        assert result == "jane.doe@catchall.com"

    def test_cleans_name_suffixes(self):
        """Names with credentials like ', MBA' should be cleaned."""
        import enrichment.email_guesser as eg
        eg._mx_cache.clear()

        with patch("enrichment.email_guesser._get_mx_host", return_value=None):
            result = guess_email("Jane, MBA", "Doe, PHR", "acme.com")
            assert result == "jane.doe@acme.com"

    def test_handles_multi_word_last_name(self):
        import enrichment.email_guesser as eg
        eg._mx_cache.clear()

        with patch("enrichment.email_guesser._get_mx_host", return_value=None):
            result = guess_email("Jane", "Van Der Berg", "acme.com")
            assert result == "jane.berg@acme.com"
