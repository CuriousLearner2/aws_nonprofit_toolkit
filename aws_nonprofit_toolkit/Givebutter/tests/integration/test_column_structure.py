"""
Test that processor output has correct column order and all required fields.

This catches regressions where columns are added/removed/reordered that would
break the template rendering alignment.
"""

import pytest
import pandas as pd
from pathlib import Path


@pytest.mark.integration
class TestProcessorColumnStructure:
    """Verify processor output has expected columns in expected order."""

    def test_processor_output_has_required_data_columns(self, temp_dir, rules_config, reference_config):
        """Test that processor output includes all required data columns."""
        from scripts.processor import process_csv

        csv_content = """Donation ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign
GB001,2026-05-25,John Smith,john@gmail.com,5551234567,100.00,123 Main St,New York,NY,Annual
GB002,2026-05-25,Jane Doe,jane@gmai.com,5559876543,50.00,456 Oak Ave,Boston,MA,Monthly"""

        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_content)
        output_file = temp_dir / "output.csv"

        process_csv(str(input_file), str(output_file))
        df = pd.read_csv(output_file, dtype=str)

        # Verify all original columns are present
        required_data_cols = ['Donation ID', 'Date', 'Donor Name', 'Email', 'Phone', 'Amount',
                              'Address 1', 'City', 'State', 'Campaign']
        for col in required_data_cols:
            assert col in df.columns, f"Missing required column: {col}"

    def test_processor_output_has_validation_columns(self, temp_dir, rules_config, reference_config):
        """Test that processor adds Validation_Tier, Issues, Suggested_Modifications columns."""
        from scripts.processor import process_csv

        csv_content = """Donation ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign
GB001,2026-05-25,John Smith,john@gmail.com,5551234567,100.00,123 Main St,New York,NY,Annual"""

        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_content)
        output_file = temp_dir / "output.csv"

        process_csv(str(input_file), str(output_file))
        df = pd.read_csv(output_file, dtype=str)

        # Verify validation columns are present
        assert 'Validation_Tier' in df.columns, "Missing Validation_Tier column"
        assert 'Issues' in df.columns, "Missing Issues column"
        assert 'Suggested_Modifications' in df.columns, "Missing Suggested_Modifications column"

    def test_processor_output_column_order(self, temp_dir, rules_config, reference_config):
        """Test that processor outputs columns in correct order: data columns first, validation last."""
        from scripts.processor import process_csv

        csv_content = """Donation ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign
GB001,2026-05-25,John Smith,john@gmail.com,5551234567,100.00,123 Main St,New York,NY,Annual"""

        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_content)
        output_file = temp_dir / "output.csv"

        process_csv(str(input_file), str(output_file))
        df = pd.read_csv(output_file, dtype=str)

        # Verify validation columns are at the END
        last_three_cols = list(df.columns)[-3:]
        assert last_three_cols == ['Validation_Tier', 'Issues', 'Suggested_Modifications'], \
            f"Validation columns not at end. Last 3 cols: {last_three_cols}"

    def test_processor_handles_various_column_names(self, temp_dir, rules_config, reference_config):
        """Test that processor handles fuzzy column name matching for optional/variant columns."""
        from scripts.processor import process_csv

        # CSV with variant column names (Phone Number instead of Phone, Donor Name variations)
        csv_content = """Donation ID,Date,Contributor Name,Email Address,Phone Number,Amount,Street Address,City,State,Fund
GB001,2026-05-25,Jane Smith,jane@gmail.com,5551234567,150.00,789 Elm St,Chicago,IL,Capital"""

        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_content)
        output_file = temp_dir / "output.csv"

        process_csv(str(input_file), str(output_file))
        df = pd.read_csv(output_file, dtype=str)

        # Verify it processed without errors and has validation columns
        assert 'Validation_Tier' in df.columns
        assert len(df) == 1
        assert df.iloc[0]['Validation_Tier'] in ['PASS', 'WARNING', 'FAIL']

    def test_processor_preserves_all_original_columns(self, temp_dir, rules_config, reference_config):
        """Test that processor preserves all original CSV columns plus adds validation columns."""
        from scripts.processor import process_csv

        csv_content = """Donation ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign,Payment Method,Notes
GB001,2026-05-25,John Smith,john@gmail.com,5551234567,100.00,123 Main St,New York,NY,Annual,Credit Card,Test donation"""

        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_content)
        output_file = temp_dir / "output.csv"

        process_csv(str(input_file), str(output_file))
        df = pd.read_csv(output_file, dtype=str)

        # Original columns should all be preserved
        original_cols = ['Donation ID', 'Date', 'Donor Name', 'Email', 'Phone', 'Amount',
                        'Address 1', 'City', 'State', 'Campaign', 'Payment Method', 'Notes']
        for col in original_cols:
            assert col in df.columns, f"Original column removed: {col}"

        # Verify data is preserved
        assert df.iloc[0]['Donor Name'] == 'John Smith'
        assert df.iloc[0]['Notes'] == 'Test donation'
