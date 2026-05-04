import pytest
from aws_nonprofit_toolkit.uncover_signal_no_pandas import analyze_bias

def test_analyze_bias_strong_signal(tmp_path, capsys):
    """Verify that bias analysis correctly detects a strong signal."""
    csv_file = tmp_path / "test_interactions.csv"
    with open(csv_file, "w") as f:
        f.write("USER_ID,ITEM_ID,TIMESTAMP,EVENT_TYPE\n")
        # Group A (0-499)
        f.write("user_0,CLEAN_WATER,12345,VIEW\n")
        f.write("user_1,CLEAN_WATER,12345,VIEW\n")
        # Group B (500+)
        f.write("user_500,EDUCATION,12345,VIEW\n")
        f.write("user_501,EDUCATION,12345,VIEW\n")

    analyze_bias(str(csv_file), threshold=20.0)
    
    captured = capsys.readouterr()
    assert "✅ STRONG SIGNAL DETECTED" in captured.out
    assert "Shift Intensity: 100.00%" in captured.out

def test_analyze_bias_weak_signal(tmp_path, capsys):
    """Verify that bias analysis correctly rejects a weak signal."""
    csv_file = tmp_path / "test_interactions_weak.csv"
    with open(csv_file, "w") as f:
        f.write("USER_ID,ITEM_ID,TIMESTAMP,EVENT_TYPE\n")
        # Group A (0-499) - mostly random
        f.write("user_0,CLEAN_WATER,12345,VIEW\n")
        f.write("user_1,EDUCATION,12345,VIEW\n")
        # Group B (500+) - also random
        f.write("user_500,CLEAN_WATER,12345,VIEW\n")
        f.write("user_501,CLEAN_WATER,12345,VIEW\n")

    # Group A: 50% Water, 50% Edu
    # Group B: 100% Water, 0% Edu
    # Diff = 50% (should pass 20% but let's test a higher threshold)
    analyze_bias(str(csv_file), threshold=60.0)
    
    captured = capsys.readouterr()
    assert "❌ WEAK SIGNAL" in captured.out
    assert "Threshold: 60.0%" in captured.out

def test_analyze_bias_invalid_file(capsys):
    """Verify error handling for missing files."""
    analyze_bias("non_existent.csv")
    captured = capsys.readouterr()
    assert "Error: File non_existent.csv not found." in captured.out
