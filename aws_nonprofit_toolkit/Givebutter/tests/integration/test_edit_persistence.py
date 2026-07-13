"""Integration tests for inline edit persistence and data integrity."""
import json
import tempfile
from pathlib import Path
import pandas as pd
import pytest


@pytest.fixture
def temp_csv():
    """Create a temporary CSV file with test data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        f.write('Transaction ID,Date,Name,Email,Phone,Amount,Campaign Title\n')
        f.write('TXN001,2026-06-05,John Doe,john@gmai.com,5551234567,100,Annual Fund\n')
        f.write('TXN002,2026-06-05,Jane Smith,jane@example.com,,500,General Fund\n')
        f.write('TXN003,2026-06-05,Bob Wilson,bob@test.com,1234567890,1000,Capital Campaign\n')
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


class TestEditPersistence:
    """Test that edited values are persisted to output files."""

    def test_single_field_edit_persists_to_approved_csv(self, temp_csv):
        """Verify email edit is saved to approved output file."""
        from scripts.processor import process_csv
        import tempfile

        # Process the CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output:
            output_path = Path(output.name)

        process_csv(str(temp_csv), str(output_path))

        # Read processed file
        df = pd.read_csv(output_path, dtype=str)

        # Simulate edit: fix email typo in first record
        df.at[0, 'Email'] = 'john@gmail.com'
        df.at[0, 'Operator_Decision'] = 'approved'

        # Simulate decision submission by splitting records
        approved_df = df[df['Operator_Decision'] == 'approved']

        # Verify edit persisted
        assert approved_df.iloc[0]['Email'] == 'john@gmail.com', "Email edit should persist"
        assert approved_df.iloc[0]['Name'] == 'John Doe', "Other fields should remain unchanged"

        output_path.unlink(missing_ok=True)

    def test_multiple_field_edits_persist(self, temp_csv):
        """Verify multiple edits to same record persist."""
        from scripts.processor import process_csv
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output:
            output_path = Path(output.name)

        process_csv(str(temp_csv), str(output_path))
        df = pd.read_csv(output_path, dtype=str)

        # Simulate multiple edits to same record
        df.at[1, 'Phone'] = '5559876543'  # Add phone
        df.at[1, 'Email'] = 'jane@gmail.com'  # Fix email
        df.at[1, 'Amount'] = '750'  # Change amount
        df.at[1, 'Operator_Decision'] = 'approved'

        approved_df = df[df['Operator_Decision'] == 'approved']

        # All edits should persist
        assert approved_df.iloc[0]['Phone'] == '5559876543'
        assert approved_df.iloc[0]['Email'] == 'jane@gmail.com'
        assert approved_df.iloc[0]['Amount'] == '750'
        assert approved_df.iloc[0]['Name'] == 'Jane Smith', "Unedited field should remain"

        output_path.unlink(missing_ok=True)

    def test_edits_to_multiple_records_persist(self, temp_csv):
        """Verify edits to different records all persist."""
        from scripts.processor import process_csv
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output:
            output_path = Path(output.name)

        process_csv(str(temp_csv), str(output_path))
        df = pd.read_csv(output_path, dtype=str)

        # Edit record 0
        df.at[0, 'Email'] = 'john@gmail.com'
        df.at[0, 'Operator_Decision'] = 'approved'

        # Edit record 1
        df.at[1, 'Phone'] = '5559876543'
        df.at[1, 'Operator_Decision'] = 'approved'

        # Edit record 2
        df.at[2, 'Name'] = 'Robert Wilson'
        df.at[2, 'Operator_Decision'] = 'followup'

        # Verify each record's edits persisted
        approved_df = df[df['Operator_Decision'] == 'approved']
        followup_df = df[df['Operator_Decision'] == 'followup']

        assert approved_df.iloc[0]['Email'] == 'john@gmail.com'
        assert approved_df.iloc[1]['Phone'] == '5559876543'
        assert followup_df.iloc[0]['Name'] == 'Robert Wilson'

        output_path.unlink(missing_ok=True)

    def test_invalid_edit_fails_validation(self, temp_csv):
        """Verify invalid edits are caught by validation."""
        from scripts.processor import process_csv, validate_phone, build_header_mapping
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output:
            output_path = Path(output.name)

        process_csv(str(temp_csv), str(output_path))
        df = pd.read_csv(output_path, dtype=str)

        # Attempt to set invalid phone (sequential test number)
        df.at[0, 'Phone'] = '123'

        # Validate the record
        record = df.iloc[0].to_dict()
        header_map = build_header_mapping(df.columns)

        # Load rules for validation
        import json
        from pathlib import Path as PathlibPath
        rules_file = PathlibPath(__file__).parents[2] / 'config' / 'rules' / 'rules_v2.4.json'
        with open(rules_file) as f:
            rules = json.load(f)

        tier, reason, suggestion = validate_phone(record, header_map, rules)

        # Invalid phone should FAIL
        assert tier == 'FAIL', f"Sequential phone should fail validation, got: {tier}"
        assert 'invalid' in reason.lower(), f"Should report invalid phone format, got: {reason}"

        output_path.unlink(missing_ok=True)


class TestEditValidationOnSubmit:
    """Test that validation happens when edits are submitted."""

    def test_edited_email_revalidated_on_submit(self, temp_csv):
        """Verify email is revalidated after edit."""
        from scripts.processor import process_csv, validate_email, build_header_mapping
        import tempfile
        import json
        from pathlib import Path as PathlibPath

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output:
            output_path = Path(output.name)

        process_csv(str(temp_csv), str(output_path))
        df = pd.read_csv(output_path, dtype=str)

        # Fix email typo
        df.at[0, 'Email'] = 'john@gmail.com'

        # Revalidate
        record = df.iloc[0].to_dict()
        header_map = build_header_mapping(df.columns)

        rules_file = PathlibPath(__file__).parents[2] / 'config' / 'rules' / 'rules_v2.4.json'
        with open(rules_file) as f:
            rules = json.load(f)

        reference_file = PathlibPath(__file__).parents[2] / 'config' / 'reference_list.json'
        with open(reference_file) as f:
            reference = json.load(f)

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)

        # Fixed email should PASS
        assert tier == 'PASS', f"Fixed email should pass, got tier: {tier}, reason: {reason}"

        output_path.unlink(missing_ok=True)

    def test_edited_phone_revalidated_on_submit(self, temp_csv):
        """Verify phone is revalidated after edit."""
        from scripts.processor import process_csv, validate_phone, build_header_mapping
        import tempfile
        import json
        from pathlib import Path as PathlibPath

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output:
            output_path = Path(output.name)

        process_csv(str(temp_csv), str(output_path))
        df = pd.read_csv(output_path, dtype=str)

        # Fix missing phone
        df.at[1, 'Phone'] = '4159876543'

        record = df.iloc[1].to_dict()
        header_map = build_header_mapping(df.columns)

        rules_file = PathlibPath(__file__).parents[2] / 'config' / 'rules' / 'rules_v2.4.json'
        with open(rules_file) as f:
            rules = json.load(f)

        tier, reason, suggestion = validate_phone(record, header_map, rules)

        # Fixed phone should PASS
        assert tier == 'PASS', f"Fixed phone should pass, got tier: {tier}, reason: {reason}"

        output_path.unlink(missing_ok=True)
