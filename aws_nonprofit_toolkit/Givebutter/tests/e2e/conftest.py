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
import requests


def wait_for_flask_ready(base_url: str, timeout_seconds: int = 10) -> None:
	"""
	Wait for Flask server to become ready by polling the health endpoint.

	Uses exponential backoff starting at 0.1s, bounded by timeout_seconds.
	Raises RuntimeError if Flask never becomes ready.
	"""
	start_time = time.time()
	wait_interval = 0.1
	max_interval = 1.0

	while time.time() - start_time < timeout_seconds:
		try:
			response = requests.get(f'{base_url}/health', timeout=2)
			if response.status_code == 200:
				return
		except (requests.ConnectionError, requests.Timeout):
			pass

		time.sleep(wait_interval)
		wait_interval = min(wait_interval * 1.5, max_interval)

	raise RuntimeError(f"Flask app failed to become ready at {base_url}/health after {timeout_seconds}s")


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


@pytest.fixture(scope="function")
def flask_app_database_mode():
    """Start Flask app for a single test with database mode enabled.

    This fixture is function-scoped and starts a fresh Flask instance
    with database mode enabled for each test that uses it.

    This is slower than session-scoped but ensures each test has:
    - Fresh database with no prior data
    - Fresh Flask process with correct environment variables
    - Proper cleanup between tests
    """
    import tempfile

    # Kill any existing Flask processes on port 8000
    try:
        os.system("lsof -i :8000 | grep -v LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null || true")
    except:
        pass
    time.sleep(1)  # Wait for port to be released

    # Create fresh database for this test
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    database_url = f'sqlite:///{db_path}'

    # Initialize database schema
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    app_path = Path(__file__).parent.parent.parent / "scripts" / "uploader" / "app.py"

    # Prepare environment for subprocess
    env = os.environ.copy()
    env['HOUSEHOLDER_REPOSITORY'] = 'database'
    env['GIVEBUTTER_DATABASE_URL'] = database_url
    env['HOUSEHOLDER_INGEST_ON_UPLOAD'] = 'true'
    env['FLASK_ENV'] = 'development'

    # Start Flask in subprocess on a different port (avoid conflicts with session-scoped fixture)
    # NOT piping stdout/stderr so we can see logs for debugging
    # Use port 8001 to avoid conflicts with port 8000 (used by session-scoped fixture)
    app_path_str = str(app_path)
    process = subprocess.Popen(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, '{app_path_str.rsplit('/', 1)[0]}'); from app import app; app.run(host='127.0.0.1', port=8001, debug=False)"],
        env=env,
        cwd=str(app_path.parent),
        preexec_fn=os.setsid  # Create new process group for cleanup
    )

    # Wait for app to start with bounded readiness polling on port 8001
    def wait_for_flask_ready_8001(timeout_seconds: int = 10) -> None:
        import requests
        start_time = time.time()
        wait_interval = 0.1
        max_interval = 1.0
        while time.time() - start_time < timeout_seconds:
            try:
                response = requests.get('http://127.0.0.1:8001/health', timeout=2)
                if response.status_code == 200:
                    return
            except (requests.ConnectionError, requests.Timeout):
                pass
            time.sleep(wait_interval)
            wait_interval = min(wait_interval * 1.5, max_interval)
        raise RuntimeError(f"Flask app failed to become ready on port 8001 after {timeout_seconds}s")

    try:
        wait_for_flask_ready_8001(timeout_seconds=10)
    except RuntimeError as e:
        # If Flask still won't start, kill the process and raise
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            pass
        raise

    yield process, database_url, db_path

    # Cleanup
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except Exception:
        pass

    # Cleanup database
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

    # Wait for app to start with bounded readiness polling
    wait_for_flask_ready('http://127.0.0.1:8000', timeout_seconds=10)

    yield process, database_url, db_path

    # Cleanup
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except Exception:
        pass
