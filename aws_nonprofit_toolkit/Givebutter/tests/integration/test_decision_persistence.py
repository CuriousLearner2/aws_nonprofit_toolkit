"""Integration tests for decision persistence."""
import pytest
import pandas as pd
import json
from pathlib import Path
import shutil


class TestDecisionPersistence:
    """Test decision saving and persistence across sessions."""

    @pytest.mark.integration
    def test_save_single_decision(self, temp_dir, sample_csv):
        """Test saving a single decision."""
        # Setup processing file
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Add decision to first record
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'approved'
        df.at[0, 'Operator_Notes'] = 'Looks good'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify decision persisted
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert df_verify.loc[0, 'Operator_Decision'] == 'approved'
        assert df_verify.loc[0, 'Operator_Notes'] == 'Looks good'

    @pytest.mark.integration
    def test_save_multiple_decisions(self, temp_dir, sample_csv):
        """Test saving multiple decisions."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Add decisions to multiple records
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'approved'
        df.at[1, 'Operator_Decision'] = 'followup'
        df.at[1, 'Operator_Notes'] = 'Verify phone'
        df.at[2, 'Operator_Decision'] = 'rejected'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify all decisions persisted
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert df_verify.loc[0, 'Operator_Decision'] == 'approved'
        assert df_verify.loc[1, 'Operator_Decision'] == 'followup'
        assert df_verify.loc[2, 'Operator_Decision'] == 'rejected'

    @pytest.mark.integration
    def test_partial_save_preserves_decisions(self, temp_dir, sample_csv):
        """Test that partial save preserves existing decisions."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # First session: save 2 decisions
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'approved'
        df.at[1, 'Operator_Decision'] = 'followup'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Second session: add decision to remaining record
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[2, 'Operator_Decision'] = 'rejected'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify all decisions persisted
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert df_verify.loc[0, 'Operator_Decision'] == 'approved'
        assert df_verify.loc[1, 'Operator_Decision'] == 'followup'
        assert df_verify.loc[2, 'Operator_Decision'] == 'rejected'

    @pytest.mark.integration
    def test_decision_with_notes(self, temp_dir, sample_csv):
        """Test saving decisions with operator notes."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Add decision with notes
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'followup'
        df.at[0, 'Operator_Notes'] = 'Verify email domain - possible typo'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify notes persisted
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert 'email domain' in df_verify.loc[0, 'Operator_Notes'].lower()

    @pytest.mark.integration
    def test_decision_overwrite(self, temp_dir, sample_csv):
        """Test overwriting a previous decision."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # First save: approved
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'approved'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify first decision
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert df_verify.loc[0, 'Operator_Decision'] == 'approved'

        # Change decision to rejected
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'rejected'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify updated decision
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert df_verify.loc[0, 'Operator_Decision'] == 'rejected'

    @pytest.mark.integration
    def test_no_decision_vs_empty_string(self, temp_dir, sample_csv):
        """Test that missing decision is different from empty string."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')

        # Record 0: has decision
        df.at[0, 'Operator_Decision'] = 'approved'
        # Record 1: explicitly empty (no decision)
        df.at[1, 'Operator_Decision'] = ''

        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify distinction
        # Note: pandas converts empty strings to NaN when reading without keep_default_na=False
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8', keep_default_na=False)
        assert df_verify.loc[0, 'Operator_Decision'] == 'approved'
        assert df_verify.loc[1, 'Operator_Decision'] == ''

    @pytest.mark.integration
    def test_utf8_notes_persist(self, temp_dir, sample_csv):
        """Test that UTF-8 characters in notes are preserved."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Add decision with UTF-8 notes
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'followup'
        df.at[0, 'Operator_Notes'] = 'Verify: José García - 北京'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify UTF-8 preserved
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert 'José' in df_verify.loc[0, 'Operator_Notes']
        assert '北京' in df_verify.loc[0, 'Operator_Notes']

    @pytest.mark.integration
    def test_decision_columns_initialized(self, temp_dir, sample_csv):
        """Test that decision columns are initialized when missing."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        # CSV doesn't have decision columns initially
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert 'Operator_Decision' not in df.columns
        assert 'Operator_Notes' not in df.columns

        # Add columns
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify columns exist
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        assert 'Operator_Decision' in df_verify.columns
        assert 'Operator_Notes' in df_verify.columns
        assert len(df_verify) == len(df)

    @pytest.mark.integration
    def test_decision_for_all_valid_decision_types(self, temp_dir, sample_csv):
        """Test saving all valid decision types."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Add all three decision types
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        valid_decisions = ['approved', 'followup', 'rejected']
        for i, decision in enumerate(valid_decisions):
            df.at[i, 'Operator_Decision'] = decision

        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Verify all decisions persisted correctly
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        for i, decision in enumerate(valid_decisions):
            assert df_verify.loc[i, 'Operator_Decision'] == decision

    @pytest.mark.integration
    def test_undecided_count_calculation(self, temp_dir, sample_csv):
        """Test calculating count of undecided records."""
        processing_file = temp_dir / "processing.csv"
        shutil.copy(sample_csv, processing_file)

        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df['Operator_Decision'] = ''
        df['Operator_Notes'] = ''
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Add some decisions
        df = pd.read_csv(processing_file, dtype=str, encoding='utf-8')
        df.at[0, 'Operator_Decision'] = 'approved'
        df.at[1, 'Operator_Decision'] = 'followup'
        df.to_csv(processing_file, index=False, encoding='utf-8')

        # Calculate undecided
        # Use keep_default_na=False to preserve empty strings as '' instead of NaN
        df_verify = pd.read_csv(processing_file, dtype=str, encoding='utf-8', keep_default_na=False)
        undecided_count = len(df_verify[df_verify['Operator_Decision'] == ''])

        # Should have 2 undecided records (original had 4 total)
        assert undecided_count == 2
