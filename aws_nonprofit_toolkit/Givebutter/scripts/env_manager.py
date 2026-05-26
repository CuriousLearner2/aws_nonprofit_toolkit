"""
env_manager.py
Auto-discovers latest rules + ensures intake/review folders exist.
Import this at the top of any script:  import scripts.env_manager
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv, set_key

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # Givebutter/
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

def get_latest_versioned_file(folder: Path, prefix: str):
    files = sorted(folder.glob(f"{prefix}_v*.*"))
    if not files:
        return None
    # sort by version number
    def ver(f):
        try:
            return float(f.stem.split("_v")[1])
        except:
            return 0
    return sorted(files, key=ver)[-1]

def discover_and_sync_paths():
    # 1. Rules auto-discovery
    rules_dir = PROJECT_ROOT / "config" / "rules"
    schemas_dir = PROJECT_ROOT / "config" / "schemas"
    
    latest_rule = get_latest_versioned_file(rules_dir, "rules")
    latest_schema = get_latest_versioned_file(schemas_dir, "rules_schema")
    
    if latest_rule:
        rel_rule = latest_rule.relative_to(PROJECT_ROOT).as_posix()
        set_key(str(ENV_PATH), "RULES_FILE", rel_rule)
        os.environ["RULES_FILE"] = rel_rule
        print(f"[env] RULES_FILE: {rel_rule}")
    
    if latest_schema:
        rel_schema = latest_schema.relative_to(PROJECT_ROOT).as_posix()
        set_key(str(ENV_PATH), "RULES_SCHEMA_FILE", rel_schema)
        os.environ["RULES_SCHEMA_FILE"] = rel_schema

    # 2. Ensure intake/review directories exist
    dirs = {
        "INTAKE_DIR": "intake/new",
        "INTAKE_FAILED_DIR": "intake/failed",
        "INTAKE_ARCHIVE_DIR": "intake/archive",
        "REVIEW_FLAGGED_DIR": "review/flagged",
        "REVIEW_APPROVED_DIR": "review/approved",
        "REVIEW_REJECTED_DIR": "review/rejected",
    }
    
    for key, default in dirs.items():
        val = os.getenv(key, default)
        path = PROJECT_ROOT / val
        path.mkdir(parents=True, exist_ok=True)
        # persist default if missing
        if not os.getenv(key):
            set_key(str(ENV_PATH), key, default)
        print(f"[env] {key}: {path}")

# run on import
discover_and_sync_paths()
