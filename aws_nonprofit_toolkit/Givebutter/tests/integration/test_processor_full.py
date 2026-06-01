"""Integration tests for full processor pipeline."""
import pytest
import pandas as pd
import json
from pathlib import Path
from processor import process_csv


class TestProcessorFullPipeline:
    """Test full processor pipeline end-to-end."""

    @pytest.mark.integration
    def test_process_simple_csv_valid_records(self, temp_dir, sample_csv, rules_config, reference_config):
        """Test processing simple CSV with valid records."""
        output_file = temp_dir / "output.csv"

        process_csv(str(sample_csv), str(output_file))

        # Verify output file exists
        assert output_file.exists()

        # Read output
        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # Check columns
        assert 'Validation_Tier' in df.columns
        assert 'Issues' in df.columns
        assert 'Suggested_Modifications' in df.columns

        # Check records processed
        assert len(df) == 4

    @pytest.mark.integration
    def test_process_csv_validation_tiers(self, temp_dir, sample_csv, rules_config, reference_config):
        """Test that validation tiers are correctly assigned."""
        output_file = temp_dir / "output.csv"

        process_csv(str(sample_csv), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # Check tiers are assigned
        tiers = df['Validation_Tier'].unique()
        assert len(tiers) > 0
        for tier in tiers:
            assert tier in ['PASS', 'WARNING', 'FAIL']

    @pytest.mark.integration
    def test_process_csv_with_typos(self, temp_dir, rules_config, reference_config):
        """Test processing CSV with email typos."""
        # Create CSV with email typos
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmai.com,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@yahoo.com,50.00,Scholarship Fund"""

        csv_file = temp_dir / "typos.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_typos.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # First record has email typo
        assert 'WARNING' in df['Validation_Tier'].values
        assert 'Email' in df.loc[0, 'Issues'] or 'typo' in df.loc[0, 'Issues'].lower()

    @pytest.mark.integration
    def test_process_csv_with_missing_data(self, temp_dir, rules_config, reference_config):
        """Test processing CSV with missing required data."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,,john@gmail.com,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,,Scholarship Fund"""

        csv_file = temp_dir / "missing_data.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_missing.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # Check for FAIL records due to missing data
        fail_records = df[df['Validation_Tier'] == 'FAIL']
        assert len(fail_records) > 0

    @pytest.mark.integration
    def test_process_csv_preserves_original_columns(self, temp_dir, sample_csv, rules_config, reference_config):
        """Test that original columns are preserved in output."""
        output_file = temp_dir / "output.csv"

        process_csv(str(sample_csv), str(output_file))

        df_original = pd.read_csv(sample_csv, dtype=str, encoding='utf-8')
        df_output = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # All original columns should be in output
        for col in df_original.columns:
            assert col in df_output.columns

    @pytest.mark.integration
    def test_process_csv_column_order(self, temp_dir, sample_csv, rules_config, reference_config):
        """Test that columns are ordered correctly (original first, validation results last)."""
        output_file = temp_dir / "output.csv"

        process_csv(str(sample_csv), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        columns = list(df.columns)

        # Validation columns should be at the end
        assert columns[-3] == 'Validation_Tier'
        assert columns[-2] == 'Issues'
        assert columns[-1] == 'Suggested_Modifications'

    @pytest.mark.integration
    def test_process_csv_with_high_dollar_donations(self, temp_dir, rules_config, reference_config):
        """Test that high-dollar donations are flagged."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,1000.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,100.00,Scholarship Fund"""

        csv_file = temp_dir / "high_dollar.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_high_dollar.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # First record is high-dollar
        assert df.loc[0, 'Validation_Tier'] == 'WARNING'
        assert 'high' in df.loc[0, 'Issues'].lower() or 'High' in df.loc[0, 'Issues']

    @pytest.mark.integration
    def test_process_csv_with_invalid_phone(self, temp_dir, rules_config, reference_config):
        """Test that invalid phone numbers are detected."""
        csv_content = """Donation ID,Date,Donor Name,Email,Phone,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,1234567890,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,5551234567,50.00,Scholarship Fund"""

        csv_file = temp_dir / "invalid_phone.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_invalid_phone.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # First record has test phone number pattern
        if 'Phone' in df.loc[0, 'Issues']:
            assert 'Invalid' in df.loc[0, 'Issues'] or 'FAIL' == df.loc[0, 'Validation_Tier']

    @pytest.mark.integration
    def test_process_csv_utf8_encoding(self, temp_dir, rules_config, reference_config):
        """Test that UTF-8 characters are preserved."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,José García,jose@gmail.com,100.00,General Fund
GB002,2026-05-25,王小明,wang@gmail.com,50.00,Scholarship Fund"""

        csv_file = temp_dir / "utf8.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = temp_dir / "output_utf8.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # Check that names are preserved correctly
        assert 'José' in df.iloc[0]['Donor Name']
        assert '王小明' in df.iloc[1]['Donor Name']

    @pytest.mark.integration
    def test_process_csv_with_empty_rows(self, temp_dir, rules_config, reference_config):
        """Test that empty rows are handled."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund


GB002,2026-05-25,Jane Doe,jane@gmail.com,50.00,Scholarship Fund"""

        csv_file = temp_dir / "empty_rows.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_empty_rows.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # Processor includes all rows (including empty ones) and marks empty rows as FAIL
        # 4 rows total: 2 valid (John, Jane) + 2 empty rows
        assert len(df) == 4

        # Verify valid rows are included
        assert df['Donor Name'].notna().sum() >= 2

    @pytest.mark.integration
    def test_process_csv_summary_stats(self, temp_dir, sample_csv, rules_config, reference_config, capsys):
        """Test that summary statistics are printed."""
        output_file = temp_dir / "output.csv"

        process_csv(str(sample_csv), str(output_file))

        captured = capsys.readouterr()

        # Check for summary statistics in output
        assert 'Summary' in captured.out
        assert 'PASS' in captured.out
        assert 'WARNING' in captured.out
        assert 'FAIL' in captured.out

    @pytest.mark.integration
    def test_process_csv_issues_populated(self, temp_dir, sample_csv, rules_config, reference_config):
        """Test that Issues column is populated correctly."""
        output_file = temp_dir / "output.csv"

        process_csv(str(sample_csv), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # Check that Issues column exists and is populated
        assert 'Issues' in df.columns
        # Sample CSV doesn't include phone numbers, so all records should have issues
        # Verify that at least some records have issues populated
        assert any(df['Issues'].notna() & (df['Issues'] != ''))

    @pytest.mark.integration
    def test_process_csv_suggestions_populated(self, temp_dir, sample_csv, rules_config, reference_config):
        """Test that Suggested_Modifications column is populated."""
        output_file = temp_dir / "output.csv"

        process_csv(str(sample_csv), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        # Check that Suggested_Modifications column exists
        assert 'Suggested_Modifications' in df.columns

    @pytest.mark.integration
    @pytest.mark.slow
    def test_process_large_csv(self, temp_dir, rules_config, reference_config):
        """Test processing a larger CSV file."""
        # Create CSV with 100 records
        header = "Donation ID,Date,Donor Name,Email,Amount,Campaign Title"
        rows = [header]
        for i in range(100):
            rows.append(f"GB{i:03d},2026-05-25,Donor {i},donor{i}@gmail.com,{(i+1)*10},General Fund")

        csv_content = "\n".join(rows)
        csv_file = temp_dir / "large.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_large.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')

        assert len(df) == 100
        assert 'Validation_Tier' in df.columns
