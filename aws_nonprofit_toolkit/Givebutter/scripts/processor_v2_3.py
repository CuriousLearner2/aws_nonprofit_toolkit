"""
processor_v2_3.py
Givebutter donation processor - updated for intake/review structure
Run from Givebutter root: python3 -m scripts.processor_v2_3
"""

import os
import json
import shutil
import pandas as pd
from datetime import datetime
from pathlib import Path

# 1. Load env and auto-create folders
import scripts.env_manager
from dotenv import load_dotenv

ROOT = scripts.env_manager.PROJECT_ROOT
load_dotenv(ROOT / ".env")

# 2. Paths from .env (new structure)
INTAKE_DIR = ROOT / os.getenv("INTAKE_DIR", "intake/new")
INTAKE_FAILED_DIR = ROOT / os.getenv("INTAKE_FAILED_DIR", "intake/failed")
INTAKE_ARCHIVE_DIR = ROOT / os.getenv("INTAKE_ARCHIVE_DIR", "intake/archive")
REVIEW_FLAGGED_DIR = ROOT / os.getenv("REVIEW_FLAGGED_DIR", "review/flagged")
RULES_FILE = ROOT / os.getenv("RULES_FILE", "config/rules/rules_v2.4.json")

print(f"[processor] Watching: {INTAKE_DIR}")
print(f"[processor] Flagged -> {REVIEW_FLAGGED_DIR}")
print(f"[processor] Rules: {RULES_FILE}")

# 3. Load rules
try:
    with open(RULES_FILE) as f:
        rules = json.load(f)
    print(f"[processor] Loaded rules v{rules.get('version', '?')}")
except Exception as e:
    print(f"[processor] WARNING: Could not load rules: {e}")
    rules = {}

def process_file(filepath: Path):
    """Process one CSV and flag rows per rules"""
    try:
        df = pd.read_csv(filepath)
        print(f"[processor] Processing {filepath.name} ({len(df)} rows)")
        
        # --- YOUR EXISTING FLAGGING LOGIC HERE ---
        # Example: flag large donations or missing emails
        # Replace this with your actual rules_v2.4 logic
        
        flagged = pd.DataFrame()
        if not df.empty:
            # Simple demo logic - adapt to your rules
            amount_col = next((c for c in df.columns if 'amount' in c.lower()), None)
            email_col = next((c for c in df.columns if 'email' in c.lower()), None)
            
            if amount_col:
                # Flag donations > $1000 (from rules if available)
                threshold = rules.get('flag_amount_over', 1000)
                high_value = df[df[amount_col] > threshold]
                flagged = pd.concat([flagged, high_value])
            
            if email_col:
                missing_email = df[df[email_col].isna() | (df[email_col] == '')]
                flagged = pd.concat([flagged, missing_email])
            
            flagged = flagged.drop_duplicates()
        
        # --- END YOUR LOGIC ---
        
        if not flagged.empty:
            out_name = f"flagged_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filepath.name}"
            out_path = REVIEW_FLAGGED_DIR / out_name
            flagged.to_csv(out_path, index=False)
            print(f"[processor] → FLAGGED {len(flagged)} rows to {out_path.name}")
        else:
            print(f"[processor] → No flags, clean file")
        
        # Archive original
        archive_path = INTAKE_ARCHIVE_DIR / filepath.name
        shutil.move(str(filepath), str(archive_path))
        print(f"[processor] Archived to {archive_path}")
        
    except Exception as e:
        print(f"[processor] ERROR processing {filepath.name}: {e}")
        failed_path = INTAKE_FAILED_DIR / filepath.name
        shutil.move(str(filepath), str(failed_path))

def main():
    # Ensure dirs exist
    for d in [INTAKE_DIR, INTAKE_FAILED_DIR, INTAKE_ARCHIVE_DIR, REVIEW_FLAGGED_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    
    files = list(INTAKE_DIR.glob("*.csv"))
    if not files:
        print("[processor] No files to process")
        return
    
    for f in files:
        process_file(f)

if __name__ == "__main__":
    main()
