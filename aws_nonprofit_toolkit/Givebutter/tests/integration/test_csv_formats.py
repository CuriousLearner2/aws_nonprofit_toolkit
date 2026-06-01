"""Integration tests for CSV format handling."""
import pytest
import pandas as pd
from processor import process_csv


class TestCSVFormatHandling:
    """Test processor handling of various CSV formats."""

    @pytest.mark.integration
    def test_csv_with_extra_trailing_columns(self, temp_dir, rules_config, reference_config):
        """Test CSV with extra empty columns at end of rows."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title,,,
GB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund,,,
GB002,2026-05-25,Jane Doe,jane@gmail.com,50.00,Scholarship Fund,,,"""

        csv_file = temp_dir / "extra_columns.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_extra.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 2

    @pytest.mark.integration
    def test_csv_with_inconsistent_column_counts(self, temp_dir, rules_config, reference_config):
        """Test CSV where rows have different number of columns."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund,Extra Data
GB002,2026-05-25,Jane Doe,jane@gmail.com,50.00
GB003,2026-05-25,Bob Wilson,bob@gmail.com,75.00,Education,Donor,Note"""

        csv_file = temp_dir / "inconsistent.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_inconsistent.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        # All rows should be processed
        assert len(df) == 3

    @pytest.mark.integration
    def test_csv_with_quoted_fields(self, temp_dir, rules_config, reference_config):
        """Test CSV with quoted fields containing commas."""
        csv_content = '''Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,"Smith, John",john@gmail.com,100.00,General Fund
GB002,2026-05-25,"Doe, Jane",jane@gmail.com,50.00,"Education, Scholarship"'''

        csv_file = temp_dir / "quoted.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_quoted.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 2
        assert 'Smith' in df.iloc[0]['Donor Name']

    @pytest.mark.integration
    def test_csv_with_line_breaks_in_fields(self, temp_dir, rules_config, reference_config):
        """Test CSV with line breaks in quoted fields."""
        csv_content = '''Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,"John
Smith",john@gmail.com,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,50.00,Scholarship'''

        csv_file = temp_dir / "line_breaks.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_line_breaks.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 2

    @pytest.mark.integration
    def test_csv_with_windows_line_endings(self, temp_dir, rules_config, reference_config):
        """Test CSV with Windows line endings (CRLF)."""
        csv_content = "Donation ID,Date,Donor Name,Email,Amount,Campaign Title\r\nGB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund\r\nGB002,2026-05-25,Jane Doe,jane@gmail.com,50.00,Scholarship Fund\r\n"

        csv_file = temp_dir / "windows.csv"
        csv_file.write_bytes(csv_content.encode('utf-8'))

        output_file = temp_dir / "output_windows.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 2

    @pytest.mark.integration
    def test_csv_with_leading_trailing_whitespace_in_headers(self, temp_dir, rules_config, reference_config):
        """Test CSV with whitespace around column headers."""
        csv_content = """ Donation ID , Date , Donor Name , Email , Amount , Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,50.00,Scholarship Fund"""

        csv_file = temp_dir / "whitespace_headers.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_whitespace.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 2

    @pytest.mark.integration
    def test_csv_with_custom_column_order(self, temp_dir, rules_config, reference_config):
        """Test CSV with columns in different order."""
        csv_content = """Amount,Campaign Title,Date,Email,Donation ID,Donor Name
100.00,General Fund,2026-05-25,john@gmail.com,GB001,John Smith
50.00,Scholarship Fund,2026-05-25,jane@gmail.com,GB002,Jane Doe"""

        csv_file = temp_dir / "custom_order.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_custom_order.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 2
        # Should preserve original column order
        assert 'Amount' in df.columns

    @pytest.mark.integration
    def test_csv_with_duplicate_column_names(self, temp_dir, rules_config, reference_config):
        """Test CSV with duplicate column names."""
        csv_content = """Donation ID,Date,Donor Name,Email,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,john2@gmail.com,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,jane2@gmail.com,50.00,Scholarship Fund"""

        csv_file = temp_dir / "duplicate_cols.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_duplicate_cols.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        # Pandas will rename duplicate columns, but processing should still work
        assert len(df) == 2

    @pytest.mark.integration
    def test_csv_with_special_characters_in_data(self, temp_dir, rules_config, reference_config):
        """Test CSV with special characters in data."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,O'Brien-Smith,john@gmail.com,100.00,"General Fund & Donations"
GB002,2026-05-25,José García,jose@gmail.com,50.00,"Education (K-12)"
GB003,2026-05-25,李明,li@gmail.com,75.00,基金"""

        csv_file = temp_dir / "special_chars.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = temp_dir / "output_special.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 3

    @pytest.mark.integration
    def test_csv_with_empty_fields(self, temp_dir, rules_config, reference_config):
        """Test CSV with various empty fields."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,,100.00,General Fund
GB002,2026-05-25,,jane@gmail.com,50.00,Scholarship Fund
GB003,2026-05-25,Bob Wilson,bob@gmail.com,,Education Fund
GB004,2026-05-25,Alice Brown,alice@gmail.com,75.00,"""

        csv_file = temp_dir / "empty_fields.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_empty_fields.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 4

    @pytest.mark.integration
    def test_csv_with_bom_marker(self, temp_dir, rules_config, reference_config):
        """Test CSV file with UTF-8 BOM marker."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,50.00,Scholarship Fund"""

        csv_file = temp_dir / "with_bom.csv"
        # Write with UTF-8 BOM
        with open(csv_file, 'w', encoding='utf-8-sig') as f:
            f.write(csv_content)

        output_file = temp_dir / "output_bom.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 2

    @pytest.mark.integration
    def test_csv_with_currency_formatted_amounts(self, temp_dir, rules_config, reference_config):
        """Test CSV with various currency formats for amounts."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,$100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,50,Scholarship Fund
GB003,2026-05-25,Bob Wilson,bob@gmail.com,"$1,500.00",Education Fund
GB004,2026-05-25,Alice Brown,alice@gmail.com,"1,234.56",Health & Wellness"""

        csv_file = temp_dir / "currency_formats.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_currency.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 4

    @pytest.mark.integration
    def test_csv_single_row(self, temp_dir, rules_config, reference_config):
        """Test CSV with only header and one data row."""
        csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund"""

        csv_file = temp_dir / "single_row.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_single.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) == 1

    @pytest.mark.integration
    def test_csv_with_numeric_strings(self, temp_dir, rules_config, reference_config):
        """Test CSV preserves numeric strings as strings."""
        csv_content = """Donation ID,Date,Donor Name,Email,Phone,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,5551234567,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmail.com,555-456-7890,50.00,Scholarship Fund"""

        csv_file = temp_dir / "numeric_strings.csv"
        csv_file.write_text(csv_content)

        output_file = temp_dir / "output_numeric.csv"
        process_csv(str(csv_file), str(output_file))

        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        # Phone should be string, not parsed as number
        assert df.iloc[0]['Phone'] in ['5551234567', '555-1234567', '5551234567']
