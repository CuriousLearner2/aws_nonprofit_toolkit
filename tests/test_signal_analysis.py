import pytest
from aws_nonprofit_toolkit.uncover_signal_no_pandas import analyze_bias

def test_analyze_bias_calculation(tmp_path, capsys):
    """Verify that bias analysis correctly detects a 100% shift in a controlled dataset."""
    # Create a small dataset where Group A only likes CLEAN_WATER and Group B only likes EDUCATION
    csv_file = tmp_path / "test_interactions.csv"
    with open(csv_file, "w") as f:
        f.write("USER_ID,ITEM_ID,TIMESTAMP,EVENT_TYPE\n")
        # Group A (0-499)
        f.write("user_0,CLEAN_WATER,12345,VIEW\n")
        f.write("user_1,CLEAN_WATER,12345,VIEW\n")
        # Group B (500+)
        f.write("user_500,EDUCATION,12345,VIEW\n")
        f.write("user_501,EDUCATION,12345,VIEW\n")

    analyze_bias(str(csv_file))
    
    captured = capsys.readouterr()
    # Verification: Group A should be 100% CLEAN_WATER, Group B 0%
    assert "CLEAN_WATER          |   100.00% |     0.00%" in captured.out
    assert "SIGNAL DETECTED: Group A shows a bias toward 'CLEAN_WATER'." in captured.out
    assert "Shift Intensity: 100.00%" in captured.out

def test_analyze_bias_invalid_file(capsys):
    """Verify error handling for missing files."""
    analyze_bias("non_existent.csv")
    captured = capsys.readouterr()
    assert "Error: File non_existent.csv not found." in captured.out
