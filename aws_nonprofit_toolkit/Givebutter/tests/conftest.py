"""Pytest configuration and fixtures for Givebutter tests."""
import pytest
import tempfile
import json
from pathlib import Path
import sys
import shutil
import subprocess
import time
import os
import signal
import requests

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

# Define base directories for cleanup
BASE_DIR = Path(__file__).resolve().parents[2] / "Givebutter"
INTAKE_DIR = BASE_DIR / "intake" / "new"
PROCESSING_DIR = BASE_DIR / "review" / "processing"
APPROVED_DIR = BASE_DIR / "review" / "approved"
FOLLOWUP_DIR = BASE_DIR / "review" / "followup"
REJECTED_DIR = BASE_DIR / "review" / "rejected"
ARCHIVE_DIR = BASE_DIR / "archive"


def cleanup_csv_files():
    """Clean up CSV files in test directories."""
    for directory in [INTAKE_DIR, PROCESSING_DIR, APPROVED_DIR, FOLLOWUP_DIR, REJECTED_DIR, ARCHIVE_DIR]:
        if directory.exists():
            for csv_file in directory.glob("*.csv"):
                try:
                    csv_file.unlink()
                except Exception as e:
                    pass  # Silently ignore cleanup errors


def is_flask_healthy(timeout=2):
    """Check if Flask app is responding to health check requests."""
    try:
        response = requests.get('http://127.0.0.1:8000/health', timeout=timeout)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout, Exception):
        return False


def restart_flask_process(process, retry_attempts=3):
    """Attempt to restart Flask process if it's unresponsive."""
    # Kill old process
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except:
        pass

    # Start new process
    for attempt in range(retry_attempts):
        app_path = Path(__file__).parent.parent / "scripts" / "uploader" / "app.py"
        new_process = subprocess.Popen(
            [sys.executable, str(app_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

        time.sleep(2)

        # Check if new process is healthy
        if is_flask_healthy():
            return new_process

    return None  # Failed to restart


@pytest.fixture(scope="session", autouse=True)
def cleanup_e2e_artifacts():
    """Clean up test artifact files before and after all E2E tests."""
    cleanup_csv_files()  # Clean before tests start
    yield  # Run tests

    cleanup_csv_files()  # Clean after tests complete


@pytest.fixture(scope="session")
def flask_app_running():
    """Start Flask app for E2E testing with health monitoring.

    Automatically restarts Flask if it becomes unresponsive.
    """
    app_path = Path(__file__).parent.parent / "scripts" / "uploader" / "app.py"
    process = subprocess.Popen(
        [sys.executable, str(app_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )

    time.sleep(2)

    # Verify initial startup
    if not is_flask_healthy(timeout=5):
        raise RuntimeError("Flask app failed to start or is not responding")

    yield process

    # Cleanup
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except:
        pass


# Aliases for backwards compatibility with different test files
flask_app_for_forms = flask_app_running
flask_app_for_visual = flask_app_running
start_flask_app = flask_app_running


@pytest.fixture(scope="function")
def flask_app_isolated():
    """Function-scoped Flask for tests that need isolated state (override tests).

    Creates a fresh Flask instance for each test to prevent state pollution.
    Slower than session-scoped but ensures clean state.
    """
    app_path = Path(__file__).parent.parent / "scripts" / "uploader" / "app.py"
    process = subprocess.Popen(
        [sys.executable, str(app_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )

    time.sleep(2)

    # Verify startup
    if not is_flask_healthy(timeout=5):
        raise RuntimeError("Flask app failed to start or is not responding")

    yield process

    # Cleanup
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except:
        pass


@pytest.fixture(autouse=True)
def cleanup_between_e2e_tests(flask_app_running):
    """Clean up test artifacts and monitor Flask health between E2E tests."""
    cleanup_csv_files()  # Clean up BEFORE each test

    yield  # Run test

    cleanup_csv_files()  # Clean up AFTER each test

    # Check Flask health and restart if needed
    if not is_flask_healthy(timeout=3):
        print("\n⚠️  Flask app unresponsive - attempting restart...")
        new_process = restart_flask_process(flask_app_running)
        if new_process:
            print("✓ Flask app restarted successfully")
            # Update the fixture's process reference
            flask_app_running.__dict__.update(new_process.__dict__)
        else:
            print("✗ Flask restart failed")


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


@pytest.fixture(scope="session")
def start_flask_app():
    """Start Flask app for E2E tests and clean up after."""
    app_path = Path(__file__).parent.parent.parent / "scripts" / "uploader" / "app.py"
    process = subprocess.Popen(
        [sys.executable, str(app_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # Create new process group for cleanup
    )

    # Wait for app to start
    time.sleep(2)

    yield process

    # Cleanup: kill the entire process group
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except:
        pass
