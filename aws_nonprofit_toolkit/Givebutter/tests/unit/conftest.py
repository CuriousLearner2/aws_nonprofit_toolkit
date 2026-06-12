"""Pytest configuration for unit tests.

Minimal setup for unit tests (no Flask, no E2E requirements).
"""

import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
