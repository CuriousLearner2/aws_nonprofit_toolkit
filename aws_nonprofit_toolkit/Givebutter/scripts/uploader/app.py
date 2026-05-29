from flask import Flask, render_template, request, jsonify
from functools import wraps
import os
import re
import json
from pathlib import Path
import pandas as pd
from datetime import datetime
import shutil
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parents[2]  # Givebutter/
INTAKE_DIR = BASE_DIR / "intake" / "new"
ARCHIVE_DIR = BASE_DIR / "archive"
REVIEW_DIR = BASE_DIR / "review"
FLAGGED_DIR = REVIEW_DIR / "flagged"
RULES_FILE = BASE_DIR / "config" / "rules" / "rules_v2.4.json"

# Create dirs if missing
for d in [INTAKE_DIR, ARCHIVE_DIR, FLAGGED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Config ---
def load_rules():
    """Load rules from config file, with env var overrides."""
    try:
        with open(RULES_FILE) as f:
            rules = json.load(f)
            logger.info(f"Loaded rules from {RULES_FILE}")
    except FileNotFoundError:
        logger.warning(f"Rules file not found at {RULES_FILE}, using defaults")
        rules = {"high_dollar_threshold": 1000.0}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse rules file: {e}")
        rules = {"high_dollar_threshold": 1000.0}
    return rules

rules = load_rules()
HIGH_DOLLAR_THRESHOLD = float(os.getenv('HIGH_DOLLAR_THRESHOLD', rules.get('high_dollar_threshold', 1000.0)))
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')  # Set for authentication
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
EMAIL_TYPOS = {
    'gmai.com': 'gmail.com',
    'gmial.com': 'gmail.com',
    'gnail.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    'yahooo.com': 'yahoo.com',
    'hotmal.com': 'hotmail.com',
    'outlok.com': 'outlook.com',
}

# --- Middleware ---
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if ADMIN_TOKEN:
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if token != ADMIN_TOKEN:
                return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def validate_filename(filename: str) -> bool:
    """Prevent path traversal attacks."""
    try:
        path = FLAGGED_DIR / filename
        path.resolve().relative_to(FLAGGED_DIR.resolve())
        return filename.endswith('.csv') and path.exists()
    except (ValueError, OSError):
        return False

def correct_email(email: str) -> str:
    """Correct known email typos."""
    if '@' not in email:
        return ''
    local, domain = email.rsplit('@', 1)
    domain_lower = domain.lower()
    corrected_domain = EMAIL_TYPOS.get(domain_lower, domain_lower)
    return f"{local}@{corrected_domain}"

def is_valid_email(email: str) -> bool:
    """Validate email format."""
    return bool(EMAIL_PATTERN.match(email.lower()))

def process_csv(filepath: Path):
    """Read Givebutter CSV, flag issues, return flagged records."""
    try:
        df = pd.read_csv(filepath, dtype=str).fillna('')
    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {e}")
        return None, f"Invalid CSV format: {str(e)}"
    except Exception as e:
        logger.error(f"File read error: {e}")
        return None, f"Failed to read file: {str(e)}"

    # Normalize column names (Givebutter exports vary)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # Try to find key columns
    name_col = next((c for c in df.columns if 'name' in c), df.columns[0] if len(df.columns) > 0 else None)
    email_col = next((c for c in df.columns if 'email' in c), None)
    amount_col = next((c for c in df.columns if 'amount' in c), None)
    date_col = next((c for c in df.columns if 'date' in c), None)

    if not name_col:
        return None, "No name column found"

    flagged_rows = []

    for idx, row in df.iterrows():
        flags = []
        email = row.get(email_col, '').strip() if email_col else ''
        email_corrected = ''
        amount = 0

        # Check amount
        if amount_col:
            try:
                amount = float(str(row[amount_col]).replace('$', '').replace(',', ''))
                if amount >= HIGH_DOLLAR_THRESHOLD:
                    flags.append('high-dollar')
            except ValueError:
                logger.debug(f"Row {idx}: Could not parse amount '{row.get(amount_col)}'")

        # Check email
        if not email:
            flags.append('missing-email')
        else:
            # Check for typos first
            if '@' in email:
                domain_lower = email.split('@')[-1].lower()
                if domain_lower in EMAIL_TYPOS:
                    flags.append('email-typo')
                    email_corrected = correct_email(email)
                # Also flag if email format is invalid
                elif not is_valid_email(email):
                    flags.append('invalid-email')

        if flags:
            flagged_rows.append({
                'name': row.get(name_col, ''),
                'email': email,
                'email_corrected': email_corrected,
                'amount': f"${amount:,.2f}" if amount else '',
                'donation_date': row.get(date_col, '') if date_col else '',
                'flag_reason': '|'.join(flags)
            })

    return flagged_rows, None

@app.route('/')
def index():
    return render_template('review.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Invalid file'}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files allowed'}), 400

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"upload_{timestamp}_{file.filename}"
        save_path = INTAKE_DIR / safe_name
        file.save(str(save_path))

        # Process
        flagged_rows, error = process_csv(save_path)
        if error:
            save_path.unlink(missing_ok=True)
            return jsonify({'error': error}), 400

        flagged_count = len(flagged_rows)

        if flagged_count > 0:
            # Save flagged version
            flagged_df = pd.DataFrame(flagged_rows)
            flagged_path = FLAGGED_DIR / safe_name
            flagged_df.to_csv(flagged_path, index=False)
            logger.info(f"Flagged {flagged_count} rows in {safe_name}")
        else:
            # Archive clean file
            shutil.move(str(save_path), str(ARCHIVE_DIR / safe_name))
            logger.info(f"Archived clean file {safe_name}")

        return jsonify({
            'filename': safe_name,
            'flagged_count': flagged_count,
            'status': 'flagged' if flagged_count else 'archived'
        })
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/flagged')
def list_flagged():
    files = []
    try:
        for f in sorted(FLAGGED_DIR.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                df = pd.read_csv(f, dtype=str)
                files.append({
                    'filename': f.name,
                    'rows': len(df),
                    'mtime': f.stat().st_mtime
                })
            except pd.errors.ParserError as e:
                logger.warning(f"Failed to read {f.name}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error listing flagged files: {e}")
        return jsonify({'error': 'Failed to list files'}), 500

    return jsonify(files)

@app.route('/api/flagged/<filename>')
def get_flagged(filename):
    # Validate filename to prevent path traversal
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    path = FLAGGED_DIR / filename
    try:
        df = pd.read_csv(path, dtype=str).fillna('')
        return jsonify({'rows': df.to_dict('records')})
    except Exception as e:
        logger.error(f"Error reading {filename}: {e}")
        return jsonify({'error': 'Failed to read file'}), 500

@app.route('/api/approve/<filename>', methods=['POST'])
@require_auth
def approve(filename):
    # Validate filename to prevent path traversal
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    src = FLAGGED_DIR / filename
    try:
        shutil.move(str(src), str(ARCHIVE_DIR / filename))
        logger.info(f"Approved {filename}")
        return jsonify({'status': 'approved'})
    except Exception as e:
        logger.error(f"Error approving {filename}: {e}")
        return jsonify({'error': 'Approval failed'}), 500

@app.route('/api/approve-partial/<filename>', methods=['POST'])
@require_auth
def approve_partial(filename):
    """Approve selected rows, keep others in flagged for review."""
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    try:
        data = request.get_json() or {}
        approved_indices = set(data.get('approved_indices', []))

        if not approved_indices:
            return jsonify({'error': 'No records selected'}), 400

        src = FLAGGED_DIR / filename
        df = pd.read_csv(src, dtype=str).fillna('')

        if len(df) == 0:
            return jsonify({'error': 'File is empty'}), 400

        # Split into approved and rejected
        approved_df = df.iloc[list(approved_indices)]
        rejected_indices = set(range(len(df))) - approved_indices

        # If all approved, archive the whole file
        if len(rejected_indices) == 0:
            shutil.move(str(src), str(ARCHIVE_DIR / filename))
            logger.info(f"Approved all {len(approved_df)} records in {filename}")
            return jsonify({'status': 'approved', 'count': len(approved_df)})

        # Otherwise, save rejected back to flagged
        if len(rejected_indices) > 0:
            rejected_df = df.iloc[list(rejected_indices)]
            rejected_df.to_csv(src, index=False)
            logger.info(f"Approved {len(approved_df)}, kept {len(rejected_df)} for review in {filename}")

        return jsonify({
            'status': 'partial',
            'approved': len(approved_df),
            'remaining': len(rejected_indices)
        })
    except Exception as e:
        logger.error(f"Error in partial approval {filename}: {e}")
        return jsonify({'error': f'Approval failed: {str(e)}'}), 500

@app.route('/api/reject/<filename>', methods=['POST'])
@require_auth
def reject(filename):
    # Validate filename to prevent path traversal
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    src = FLAGGED_DIR / filename
    try:
        src.unlink()
        logger.info(f"Rejected {filename}")
        return jsonify({'status': 'rejected'})
    except Exception as e:
        logger.error(f"Error rejecting {filename}: {e}")
        return jsonify({'error': 'Rejection failed'}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok", "version": "2.5"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
