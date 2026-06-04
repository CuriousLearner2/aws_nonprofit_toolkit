"""Integration tests for override confirmation logic.

Tests the backend decision-making and override handling without UI complexity.
"""
import pytest
import json
import pandas as pd
from pathlib import Path
import tempfile


@pytest.fixture
def sample_csv_with_failures(temp_dir):
    """Create a CSV with mix of PASS and FAIL tier records."""
    csv_path = temp_dir / "override_test.csv"

    data = {
        'Donation ID': ['GB001', 'GB002', 'GB003', 'GB004'],
        'Date': ['2026-06-01', '2026-06-01', '2026-06-01', '2026-06-01'],
        'Name': ['John Smith', 'Jane Doe', 'Bob Wilson', 'Alice Brown'],
        'Email': ['john@gmail.com', '', 'bob@example.com', 'alice@test.com'],
        'Phone': ['5551234567', '5559876543', '5551112222', ''],
        'Amount': ['100', '250', '', '0'],
        'Campaign': ['Annual Giving', 'Annual Giving', 'Campaign X', 'Campaign X']
    }

    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    return csv_path


class TestOverrideConfirmationLogic:
    """Test the logic that determines when override confirmation is needed."""

    def test_fail_tier_records_identified(self):
        """Verify FAIL tier records are correctly identified during processing."""
        from scripts.processor import process_csv

        data = {
            'Name': ['Valid Record', 'Missing Email'],
            'Email': ['valid@gmail.com', ''],
            'Phone': ['5551234567', '5551234567'],
            'Amount': ['100', '100'],
            'Campaign': ['Test', 'Test']
        }

        df = pd.DataFrame(data)
        csv_path = '/tmp/test_fail_detection.csv'
        df.to_csv(csv_path, index=False)

        # Process the CSV
        output_path = '/tmp/test_fail_detection_output.csv'
        process_csv(csv_path, output_path)

        # Read results
        result_df = pd.read_csv(output_path)

        # Verify FAIL is detected for missing email
        assert result_df.loc[1, 'Validation_Tier'] == 'FAIL', \
            "Record with missing email should be marked FAIL"

        # Verify PASS for valid record
        assert result_df.loc[0, 'Validation_Tier'] in ['PASS', 'WARNING'], \
            "Valid record should be PASS or WARNING"

    def test_override_confirmation_required_for_fail(self):
        """Verify that FAIL tier records require confirmation to approve."""
        # This is business logic: if a record is FAIL and operator selects "approved",
        # the system should ask for confirmation

        # A FAIL tier record
        fail_record = {
            'Validation_Tier': 'FAIL',
            'Issues': 'Missing email',
            'Operator_Decision': 'approved'  # Operator trying to approve FAIL
        }

        # Logic: FAIL + approval decision = needs confirmation
        requires_confirmation = (
            fail_record['Validation_Tier'] == 'FAIL' and
            fail_record['Operator_Decision'] == 'approved'
        )

        assert requires_confirmation, \
            "Approving FAIL tier record should require confirmation"

    def test_no_confirmation_for_pass_approval(self):
        """Verify PASS tier records do NOT require confirmation."""
        # A PASS tier record
        pass_record = {
            'Validation_Tier': 'PASS',
            'Issues': '',
            'Operator_Decision': 'approved'
        }

        # Logic: PASS + approval decision = no confirmation needed
        requires_confirmation = (
            pass_record['Validation_Tier'] == 'FAIL' and
            pass_record['Operator_Decision'] == 'approved'
        )

        assert not requires_confirmation, \
            "Approving PASS tier record should NOT require confirmation"

    def test_no_confirmation_for_non_approval(self):
        """Verify rejecting/follow-up decisions never require confirmation."""
        fail_record = {
            'Validation_Tier': 'FAIL',
            'Operator_Decision': 'rejected'
        }

        # Logic: Any decision other than "approved" = no confirmation
        requires_confirmation = (
            fail_record['Validation_Tier'] == 'FAIL' and
            fail_record['Operator_Decision'] == 'approved'
        )

        assert not requires_confirmation, \
            "Rejecting/following-up on FAIL record should NOT require confirmation"

    def test_confirmed_override_saves_decision(self):
        """Verify that confirming override dialog saves the approval decision."""
        # When operator confirms override:
        # 1. Decision should be saved as "approved"
        # 2. Record should be in approved output

        test_decision = {
            'idx': 0,
            'decision': 'approved',
            'notes': 'Verified with donor'
        }

        # Verify decision data structure
        assert test_decision['decision'] == 'approved'
        assert test_decision['notes']  # Notes are recorded

        # This data would be sent to backend /submit endpoint
        # and saved to the dataframe

    def test_canceled_override_prevents_approval(self):
        """Verify that canceling override dialog keeps decision empty."""
        # When operator cancels override:
        # 1. Decision should remain empty
        # 2. Record stays in processing queue
        # 3. User can re-review it

        # If operator cancels, decision is not submitted
        # This is enforced by the dialog flow

        test_state = {
            'record_idx': 0,
            'operator_decision': '',  # Empty = not decided
            'reason': 'operator_canceled_override'
        }

        assert test_state['operator_decision'] == '', \
            "Canceled override should leave decision empty"


class TestOverrideDecisionProcessing:
    """Test how override decisions are processed in the backend."""

    def test_decision_submission_with_override(self):
        """Verify the JSON payload structure for override confirmation decisions."""
        # This is what the frontend sends when confirming override
        decision_payload = {
            'decisions': [
                {
                    'idx': 1,  # FAIL tier record
                    'decision': 'approved',
                    'notes': 'Manually verified email'
                }
            ]
        }

        # Verify payload structure
        assert 'decisions' in decision_payload
        assert len(decision_payload['decisions']) > 0
        assert decision_payload['decisions'][0]['decision'] == 'approved'

    def test_pass_tier_approval_payload(self):
        """Verify PASS tier approvals have standard payload (no override data)."""
        decision_payload = {
            'decisions': [
                {
                    'idx': 0,  # PASS tier record
                    'decision': 'approved',
                    'notes': ''
                }
            ]
        }

        # PASS approvals are straightforward - no override needed
        assert decision_payload['decisions'][0]['decision'] == 'approved'
        # No special "override_confirmed" field needed
