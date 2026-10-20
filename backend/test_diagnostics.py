import unittest

from app import sanitize_diagnostic


class SanitizeDiagnosticTests(unittest.TestCase):
    def test_redacts_labeled_api_key(self):
        self.assertIn("api_key=[REDACTED]", sanitize_diagnostic("api_key=secret-value"))

    def test_redacts_common_provider_token(self):
        self.assertEqual("[REDACTED]", sanitize_diagnostic("sk-1234567890abcdef"))

    def test_bounds_diagnostic_length(self):
        self.assertEqual(10, len(sanitize_diagnostic("x" * 100, limit=10)))


if __name__ == "__main__":
    unittest.main()
