"""E2E-specific conftest for database-backed Flask testing."""
import pytest
import tempfile
import time
import os
import subprocess
import sys
import signal
from pathlib import Path

# Database setup
from sqlalchemy import create_engine
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.householder.database_models import Base, create_db_engine


@pytest.fixture(scope="session")
def e2e_test_database():
    """Create a temporary database for E2E tests.

    This database is used by the Flask app running in subprocess.
    All tests share this database during the session.
    """
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'

    # Create all tables
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, db_path

    # Cleanup
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass


@pytest.fixture(scope="session")
def flask_app_e2e(e2e_test_database):
    """Start Flask app for E2E tests with database mode enabled.

    This fixture:
    1. Sets HOUSEHOLDER_REPOSITORY=database and GIVEBUTTER_DATABASE_URL
    2. Starts Flask as a subprocess with these env vars
    3. Verifies the app is responsive
    4. Yields the process
    5. Cleans up on teardown

    All E2E tests use this single Flask instance.
    """
    database_url, db_path = e2e_test_database

    app_path = Path(__file__).parent.parent.parent / "scripts" / "uploader" / "app.py"

    # Prepare environment for subprocess
    env = os.environ.copy()
    env['HOUSEHOLDER_REPOSITORY'] = 'database'
    env['GIVEBUTTER_DATABASE_URL'] = database_url
    env['FLASK_ENV'] = 'development'

    # Start Flask in subprocess with database mode enabled
    process = subprocess.Popen(
        [sys.executable, str(app_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # Create new process group for cleanup
    )

    # Wait for app to start
    time.sleep(3)

    # Verify app is healthy
    import requests
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.get('http://127.0.0.1:8000/health', timeout=2)
            if response.status_code == 200:
                break
        except (requests.ConnectionError, requests.Timeout):
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise RuntimeError("Flask app failed to start or health check failed")

    yield process, database_url, db_path

    # Cleanup
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except Exception:
        pass
