import sys
import os
import requests
import unittest
from unittest.mock import patch, MagicMock

# Ensure we can import the toolkit modules
sys.path.append(os.getcwd())

from aws_nonprofit_toolkit.meta_growth_engine import upload_donors_to_audience

class TestSyncReliability(unittest.TestCase):
    """Empirical validation of the Sync Reliability success criterion."""

    @patch('requests.post')
    def test_retry_on_transient_failure(self, mock_post):
        """Verify that exponential backoff handles transient API drops."""
        # 1. Setup: First call fails (500), second succeeds (200)
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.RequestException("Simulated Drop")
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"id": "test_id"}

        # Return failure then success
        mock_post.side_effect = [mock_response_fail, mock_response_success]

        # 2. Execute: Try to upload a small file
        # Note: We use a real file but mock the API
        users_file = "aws_nonprofit_toolkit/datasets/small_nonprofit_users.csv"
        
        # This should succeed after 1 retry
        try:
            upload_donors_to_audience("fake_aud_id", users_file, batch_size=5000)
        except Exception as e:
            self.fail(f"Upload failed despite retry logic: {e}")

        # 3. Validate: mock_post should have been called TWICE
        self.assertEqual(mock_post.call_count, 2, "Retry logic was not triggered or didn't retry enough.")
        print("\n✅ SYNC RELIABILITY VALIDATED: System recovered from transient API drop.")

if __name__ == "__main__":
    unittest.main()
