from flask import Flask, render_template, request, jsonify
from functools import wraps
import os
import json
from pathlib import Path
import pandas as pd
from datetime import datetime
import shutil
import logging
import sys

# Add parent directory to path so we can import processor
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from processor import process_csv as run_processor, check_duplicates, build_header_mapping

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parents[2]  # Givebutter/
INTAKE_DIR = BASE_DIR / "intake" / "new"
ARCHIVE_DIR = BASE_DIR / "archive"
REVIEW_DIR = BASE_DIR / "review"
PROCESSING_DIR = REVIEW_DIR / "processing"  # In-progress reviews
APPROVED_DIR = REVIEW_DIR / "approved"
FOLLOWUP_DIR = REVIEW_DIR / "followup"
REJECTED_DIR = REVIEW_DIR / "rejected"

# Create dirs if missing
for d in [INTAKE_DIR, ARCHIVE_DIR, PROCESSING_DIR, APPROVED_DIR, FOLLOWUP_DIR, REJECTED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')

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
        path = PROCESSING_DIR / filename
        path.resolve().relative_to(PROCESSING_DIR.resolve())
        return filename.endswith('.csv') and path.exists()
    except (ValueError, OSError):
        return False

@app.route('/')
def index():
    return render_template('review.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Upload CSV and run processor validation."""
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
        intake_path = INTAKE_DIR / safe_name

        # Save uploaded file
        file.save(str(intake_path))
        logger.info(f"Uploaded {safe_name}")

        # Run processor
        processed_path = PROCESSING_DIR / safe_name
        run_processor(str(intake_path), str(processed_path))

        # Read processed results
        df = pd.read_csv(processed_path, dtype=str)
        record_count = len(df)
        warning_count = len(df[df['Validation_Tier'] == 'WARNING'])
        fail_count = len(df[df['Validation_Tier'] == 'FAIL'])

        logger.info(f"Processed {record_count} records: {warning_count} warnings, {fail_count} failures")

        return jsonify({
            'filename': safe_name,
            'record_count': record_count,
            'warning_count': warning_count,
            'fail_count': fail_count,
            'status': 'processed'
        })
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/processing')
def list_processing():
    """List files in processing (being reviewed). Limited to most recent 5 files."""
    files = []
    try:
        # Get most recent 5 files sorted by modification time
        all_files = sorted(PROCESSING_DIR.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True)
        recent_files = all_files[:5]  # Limit to 5 most recent files

        for f in recent_files:
            try:
                df = pd.read_csv(f, dtype=str, encoding='utf-8')
                record_count = len(df)
                pass_count = len(df[df['Validation_Tier'] == 'PASS'])
                warning_count = len(df[df['Validation_Tier'] == 'WARNING'])
                fail_count = len(df[df['Validation_Tier'] == 'FAIL'])

                files.append({
                    'filename': f.name,
                    'rows': record_count,
                    'pass_count': pass_count,
                    'warning_count': warning_count,
                    'fail_count': fail_count,
                    'mtime': f.stat().st_mtime
                })
            except pd.errors.ParserError as e:
                logger.warning(f"Failed to read {f.name}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error listing processing files: {e}")
        return jsonify({'error': 'Failed to list files'}), 500

    return jsonify(files)

@app.route('/api/processing/<filename>')
def get_processing(filename):
    """Get records from file being processed."""
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    path = PROCESSING_DIR / filename
    try:
        df = pd.read_csv(path, dtype=str, encoding='utf-8').fillna('')
        logger.info(f"Columns in {filename}: {list(df.columns)}")

        # Convert to records with index for decision tracking
        records = []
        for idx, row in df.iterrows():
            record_dict = {
                'idx': int(idx),
                **row.to_dict()
            }
            records.append(record_dict)

        return jsonify({'records': records, 'filename': filename})
    except Exception as e:
        logger.error(f"Error reading {filename}: {e}")
        return jsonify({'error': 'Failed to read file'}), 500

@app.route('/api/processing/<filename>/submit', methods=['POST'])
@require_auth
def submit_decisions(filename):
    """
    Submit operator decisions for each record.

    Expected JSON:
    {
        "decisions": [
            {"idx": 0, "decision": "approved", "notes": ""},
            {"idx": 1, "decision": "followup", "notes": "Verify phone number"},
            {"idx": 2, "decision": "rejected", "notes": "Invalid email"}
        ]
    }
    """
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    try:
        data = request.get_json() or {}
        decisions = {d['idx']: d for d in data.get('decisions', [])}
        edits = {e['idx']: e for e in data.get('edits', [])} if data.get('edits') else {}

        if not decisions:
            return jsonify({'error': 'No decisions provided'}), 400

        processing_path = PROCESSING_DIR / filename
        df = pd.read_csv(processing_path, dtype=str, encoding='utf-8').fillna('')

        if len(df) == 0:
            return jsonify({'error': 'File is empty'}), 400

        # Initialize tracking columns if not present
        if 'Operator_Decision' not in df.columns:
            df['Operator_Decision'] = ''
        if 'Operator_Notes' not in df.columns:
            df['Operator_Notes'] = ''

        # Apply edits to the DataFrame
        # Map field names to actual column names (handling fuzzy matching)
        field_to_column = {
            'name': None,
            'email': None,
            'phone': None,
            'amount': None,
            'address_1': None,
            'city': None,
            'state': None,
            'campaign': None
        }

        # Detect actual column names from DataFrame
        for field, col in field_to_column.items():
            if field == 'name':
                for variant in ['Name', 'Donor Name', 'Full Name', 'donor_name', 'full_name']:
                    if variant in df.columns:
                        field_to_column[field] = variant
                        break
            elif field == 'email':
                for variant in ['Email', 'Email Address', 'Primary Email', 'email_address', 'primary_email']:
                    if variant in df.columns:
                        field_to_column[field] = variant
                        break
            elif field == 'phone':
                for variant in ['Phone', 'Phone Number', 'Contact Phone', 'phone_number', 'contact_phone']:
                    if variant in df.columns:
                        field_to_column[field] = variant
                        break
            elif field == 'amount':
                if 'Amount' in df.columns:
                    field_to_column[field] = 'Amount'
            elif field == 'address_1':
                for variant in ['Address 1', 'Street Address', 'Address Line 1', 'address_line_1']:
                    if variant in df.columns:
                        field_to_column[field] = variant
                        break
            elif field == 'city':
                if 'City' in df.columns:
                    field_to_column[field] = 'City'
            elif field == 'state':
                if 'State' in df.columns:
                    field_to_column[field] = 'State'
            elif field == 'campaign':
                for variant in ['Campaign Title', 'Campaign', 'Fund', 'campaign_title']:
                    if variant in df.columns:
                        field_to_column[field] = variant
                        break

        # Apply each edit to the corresponding column
        for record_idx, edit_data in edits.items():
            field = edit_data.get('field')
            value = edit_data.get('value', '')
            column = field_to_column.get(field)

            if column and 0 <= record_idx < len(df):
                df.at[record_idx, column] = value
                logger.info(f"Applied edit to {filename}[{record_idx}].{field}: {value}")

        # Re-run duplicate detection if edits were made
        if edits:
            try:
                # Load config for duplicate detection
                config_dir = BASE_DIR / "config"
                rules_file = config_dir / "rules" / "rules_v2.4.json"
                with open(rules_file) as f:
                    rules = json.load(f)

                # Build header mapping
                header_map = build_header_mapping(df.columns)

                # Convert DataFrame to list of dicts for duplicate checking
                records_list = df.to_dict('records')

                # Re-check duplicates for all records
                for idx, record in enumerate(records_list):
                    is_dup, dup_info = check_duplicates(record, records_list, header_map, rules)

                    if is_dup:
                        # Add duplicate info to Issues column
                        current_issues = df.at[idx, 'Issues'] or ''
                        if 'Duplicate' not in current_issues:
                            if current_issues:
                                df.at[idx, 'Issues'] = current_issues + f"; Duplicate: {dup_info}"
                            else:
                                df.at[idx, 'Issues'] = f"Duplicate: {dup_info}"

                        # Add suggestion for duplicates
                        current_suggestions = df.at[idx, 'Suggested_Modifications'] or ''
                        if 'Review duplicate' not in current_suggestions:
                            if current_suggestions:
                                df.at[idx, 'Suggested_Modifications'] = current_suggestions + "; Review duplicate entries"
                            else:
                                df.at[idx, 'Suggested_Modifications'] = "Review duplicate entries"

                        # Update Validation_Tier to WARNING if it was PASS
                        current_tier = df.at[idx, 'Validation_Tier']
                        if current_tier == 'PASS':
                            df.at[idx, 'Validation_Tier'] = 'WARNING'
                            logger.info(f"Updated {filename}[{idx}] tier from PASS to WARNING due to duplicate detection")

                logger.info(f"Re-validated duplicates for {filename} after applying edits")
            except Exception as e:
                logger.warning(f"Error during duplicate re-validation for {filename}: {e}")

        # Update decisions and notes
        for idx, row in df.iterrows():
            decision_data = decisions.get(int(idx), {})
            if decision_data.get('decision'):
                df.at[idx, 'Operator_Decision'] = decision_data['decision']
                if decision_data.get('notes'):
                    df.at[idx, 'Operator_Notes'] = decision_data['notes']

        # Check if all records have decisions
        undecided_count = len(df[df['Operator_Decision'] == ''])
        decided_count = len(df) - undecided_count

        # Save progress back to processing file
        df.to_csv(processing_path, index=False, encoding='utf-8')
        logger.info(f"Saved {decided_count}/{len(df)} decisions for {filename}")

        # If all records have decisions, split and archive
        if undecided_count == 0:
            # Split records by decision
            approved_records = []
            followup_records = []
            rejected_records = []

            for idx, row in df.iterrows():
                decision_type = row['Operator_Decision']
                record = row.to_dict()

                if decision_type == 'approved':
                    approved_records.append(record)
                elif decision_type == 'followup':
                    followup_records.append(record)
                elif decision_type == 'rejected':
                    rejected_records.append(record)

            # Write output files
            base_filename = filename.replace('.csv', '')

            if approved_records:
                approved_path = APPROVED_DIR / f"{base_filename}_APPROVED.csv"
                pd.DataFrame(approved_records).to_csv(approved_path, index=False, encoding='utf-8')
                logger.info(f"Wrote {len(approved_records)} approved records to {approved_path.name}")

            if followup_records:
                followup_path = FOLLOWUP_DIR / f"{base_filename}_FOLLOWUP.csv"
                pd.DataFrame(followup_records).to_csv(followup_path, index=False, encoding='utf-8')
                logger.info(f"Wrote {len(followup_records)} followup records to {followup_path.name}")

            if rejected_records:
                rejected_path = REJECTED_DIR / f"{base_filename}_REJECTED.csv"
                pd.DataFrame(rejected_records).to_csv(rejected_path, index=False, encoding='utf-8')
                logger.info(f"Wrote {len(rejected_records)} rejected records to {rejected_path.name}")

            # Archive the processed file
            archive_path = ARCHIVE_DIR / filename
            shutil.move(str(processing_path), str(archive_path))
            logger.info(f"Archived processed file {filename}")

            return jsonify({
                'status': 'complete',
                'approved': len(approved_records),
                'followup': len(followup_records),
                'rejected': len(rejected_records)
            })
        else:
            # Partial save - file remains in processing queue
            return jsonify({
                'status': 'progress_saved',
                'decided': decided_count,
                'remaining': undecided_count
            })

    except Exception as e:
        logger.error(f"Error submitting decisions for {filename}: {e}")
        return jsonify({'error': f'Submission failed: {str(e)}'}), 500

@app.route('/api/processing/<filename>/cancel', methods=['POST'])
@require_auth
def cancel_review(filename):
    """Cancel review and return file to intake."""
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    processing_path = PROCESSING_DIR / filename
    try:
        intake_path = INTAKE_DIR / filename
        shutil.move(str(processing_path), str(intake_path))
        logger.info(f"Cancelled review for {filename}")
        return jsonify({'status': 'cancelled'})
    except Exception as e:
        logger.error(f"Error cancelling review for {filename}: {e}")
        return jsonify({'error': 'Cancellation failed'}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok", "version": "3.0"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
