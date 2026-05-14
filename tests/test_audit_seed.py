import pytest
import csv
from aws_nonprofit_toolkit.audit_seed_quality import run_audit

def test_audit_strong_signal(tmp_path):
    """Verify that a Pareto-compliant dataset passes the audit."""
    csv_file = tmp_path / "strong_seed.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["USER_ID", "LTV", "LOYALTY_LEVEL"])
        # Top 10% (2 donors) hold most of the value
        writer.writerow(["u1", "1000", "VIP"])
        writer.writerow(["u2", "1000", "VIP"])
        # Remaining 18 donors hold very little
        for i in range(18):
            writer.writerow([f"u{i+3}", "10", "REGULAR"])
            
    # Total value = 2000 + 180 = 2180. Top 10% is 2000/2180 = ~91%
    assert run_audit(str(csv_file), concentration_threshold=0.60) is True

def test_audit_weak_signal(tmp_path):
    """Verify that a flat distribution fails the audit."""
    csv_file = tmp_path / "weak_seed.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["USER_ID", "LTV", "LOYALTY_LEVEL"])
        # Every donor has exactly the same value ($100)
        for i in range(20):
            writer.writerow([f"u{i}", "100", "REGULAR"])
            
    # Top 10% (2 donors) is 200/2000 = 10%. This should fail 60% threshold.
    assert run_audit(str(csv_file), concentration_threshold=0.60) is False

def test_audit_missing_file():
    """Verify handling of missing files."""
    assert run_audit("non_existent.csv") is False

def test_audit_empty_data(tmp_path):
    """Verify handling of empty CSVs."""
    csv_file = tmp_path / "empty.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["USER_ID", "LTV", "LOYALTY_LEVEL"])
    
    assert run_audit(str(csv_file)) is False
