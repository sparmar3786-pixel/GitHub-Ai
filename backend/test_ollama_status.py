import io
import json
import unittest
from unittest.mock import patch

from ollama_status import inspect_ollama


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class OllamaStatusTests(unittest.TestCase):
    def test_missing_url_is_unconfigured(self):
        result = inspect_ollama(base_url="", model="llama3.2:3b")
        self.assertEqual(result["status"], "UNCONFIGURED")
        self.assertFalse(result["reachable"])

    def test_reachable_and_model_present(self):
        payload = {"models": [{"name": "llama3.2:3b"}]}
        with patch("ollama_status.urlopen", return_value=FakeResponse(payload)):
            result = inspect_ollama("http://ollama:11434", "llama3.2:3b")
        self.assertEqual(result["status"], "READY")
        self.assertTrue(result["model_available"])

    def test_reachable_but_model_missing(self):
        with patch("ollama_status.urlopen", return_value=FakeResponse({"models": []})):
            result = inspect_ollama("http://ollama:11434", "llama3.2:3b")
        self.assertEqual(result["status"], "MODEL_MISSING")
        self.assertFalse(result["model_available"])

    def test_invalid_url_does_not_leak_credentials(self):
        result = inspect_ollama("https://user:secret@ollama.example")
        self.assertEqual(result["status"], "INVALID_CONFIGURATION")
        self.assertNotIn("secret", json.dumps(result))

    def test_connection_error_is_redacted(self):
        with patch("ollama_status.urlopen", side_effect=OSError("private host and secret")):
            result = inspect_ollama("http://ollama:11434")
        self.assertEqual(result["status"], "UNREACHABLE")
        self.assertNotIn("private host", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
