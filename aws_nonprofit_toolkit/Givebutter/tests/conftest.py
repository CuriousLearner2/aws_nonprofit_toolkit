"""Pytest configuration and fixtures for Givebutter tests."""
import pytest
import tempfile
import json
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv(temp_dir):
    """Create a sample CSV file for testing."""
    csv_content = """Donation ID,Date,Donor Name,Email,Amount
GB001,2026-05-25,John Smith,john@gmail.com,100.00
GB002,2026-05-25,Jane Doe,jane@gmai.com,50.00
GB003,2026-05-25,Bob Wilson,bob@yahoo.com,75.00
GB004,2026-05-25,Alice Brown,alice@yaho.com,200.00
"""
    csv_file = temp_dir / "sample.csv"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def rules_config(temp_dir):
    """Create a sample rules config for testing."""
    rules = {
        "email_typos": [
            {"from": "gmai.com", "to": "gmail.com"},
            {"from": "gmal.com", "to": "gmail.com"},
            {"from": "yaho.com", "to": "yahoo.com"},
            {"from": "yahooo.com", "to": "yahoo.com"},
            {"from": "hotmial.com", "to": "hotmail.com"},
            {"from": "hotmal.com", "to": "hotmail.com"},
            {"from": "outlok.com", "to": "outlook.com"},
        ],
        "invalid_phone_patterns": [
            {"pattern": r"^1234567890$", "reason": "Sequential test number"},
            {"pattern": r"^(\d)\1{9}$", "reason": "All same digit"},
            {"pattern": r"^555[0-1]\d{6}$", "reason": "Reserved test number"},
        ]
    }
    config_dir = temp_dir / "config" / "rules"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "rules_v2.4.json"
    config_file.write_text(json.dumps(rules))
    return config_file


@pytest.fixture
def reference_config(temp_dir):
    """Create a sample reference list config for testing."""
    reference = {
        "email_domains": ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"],
        "email_tlds": ["com", "org", "net", "edu"],
        "amount_statistics": {
            "valid_range": [1, 100000],
            "min": 1.0,
            "max": 100000.0,
            "avg": 500.0
        },
        "high_dollar_threshold": 1000,
        "name_patterns": {
            "min_length": 2,
            "max_length": 100
        }
    }
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "reference_list.json"
    config_file.write_text(json.dumps(reference))
    return config_file
