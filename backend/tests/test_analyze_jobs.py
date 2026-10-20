import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

# Import the application first; it registers the job router after defining its helpers.
from app import AnalyzeRequest
import analyze_jobs


class AnalyzeJobEndpointTests(unittest.TestCase):
    def test_submit_returns_job_id_without_running_analysis_inline(self):
        request = AnalyzeRequest(ticker="RELIANCE.NS", analysts=["market"])
        with patch.object(analyze_jobs, "cli_available", return_value=True), \
             patch.object(analyze_jobs, "configuration_gaps", return_value=[]), \
             patch.object(analyze_jobs._executor, "submit") as submit:
            response = analyze_jobs.submit_analyze_job(request)

        self.assertEqual(response["status"], "RUNNING")
        self.assertTrue(response["job_id"])
        self.assertEqual(response["ticker"], "RELIANCE.NS")
        submit.assert_called_once()

    def test_job_status_returns_current_snapshot(self):
        job_id = "unit-test-job"
        original = analyze_jobs._jobs.get(job_id)
        analyze_jobs._jobs[job_id] = {
            "job_id": job_id,
            "status": "RUNNING",
            "ticker": "RELIANCE.NS",
        }
        try:
            response = analyze_jobs.get_analyze_job(job_id)
            self.assertEqual(response["status"], "RUNNING")
            self.assertEqual(response["ticker"], "RELIANCE.NS")
        finally:
            if original is None:
                analyze_jobs._jobs.pop(job_id, None)
            else:
                analyze_jobs._jobs[job_id] = original

    def test_unknown_job_returns_actionable_404(self):
        with self.assertRaises(HTTPException) as caught:
            analyze_jobs.get_analyze_job("job-that-does-not-exist")
        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
