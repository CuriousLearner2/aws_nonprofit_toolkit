from flask import Flask, render_template, request, jsonify, redirect, current_app, send_file
from functools import wraps
import os
import json
from pathlib import Path
import pandas as pd
from datetime import datetime
import shutil
import logging
import sys
import tempfile

# Add parent directory to path so we can import processor
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from processor import (
    process_csv as run_processor,
    check_duplicates,
    build_header_mapping,
    validate_transaction_id,
    validate_date,
    validate_email,
    validate_amount,
    validate_name,
    validate_phone,
    validate_address,
    assign_tier,
    load_rules,
    load_reference_list
)

# Import ingestion service for optional database mode
try:
    from householder.ingestion_service import ingest_processed_csv, IngestionValidationError, IngestionIOError, IngestionDatabaseError
except ImportError:
    # Fallback for direct script execution
    from householder.ingestion_service import ingest_processed_csv, IngestionValidationError, IngestionIOError, IngestionDatabaseError

# Import fixtures for DonorTrust v1 prototype
try:
    from .fixtures import (
        IMPORT_BATCH,
        CONTACTS,
        DUPLICATE_CANDIDATES,
        NORMALIZATION_SUGGESTIONS,
        HOUSEHOLD_SUGGESTIONS,
        AUDIT_LOG_ENTRIES,
        EXPORT_CARDS,
        IMPORTS_LIST,
        QUEUE_STATUS
    )
except ImportError:
    # Fallback for direct script execution
    from fixtures import (
        IMPORT_BATCH,
        CONTACTS,
        DUPLICATE_CANDIDATES,
        NORMALIZATION_SUGGESTIONS,
        HOUSEHOLD_SUGGESTIONS,
        AUDIT_LOG_ENTRIES,
        EXPORT_CARDS,
        IMPORTS_LIST,
        QUEUE_STATUS
    )

# Import DonorTrust v1 service layer
try:
    from ..householder import (
        import_service,
        dashboard_service,
        validation_service,
        validation_decision_service,
        normalizations_service,
        normalization_decision_service,
        households_service,
        duplicates_service,
        duplicate_decision_service,
        audit_service,
        exports_service,
    )
except ImportError:
    # Fallback for direct script execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from householder import (
        import_service,
        dashboard_service,
        validation_service,
        validation_decision_service,
        normalizations_service,
        normalization_decision_service,
        households_service,
        duplicates_service,
        duplicate_decision_service,
        audit_service,
        exports_service,
    )

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

def format_relative_time(dt):
    """Format datetime as relative time string (e.g., '2h ago')."""
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f'{minutes}m ago'
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f'{hours}h ago'
    else:
        days = int(seconds // 86400)
        return f'{days}d ago'

@app.route('/')
def index():
    return render_template('review.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Upload CSV and run processor validation. Optionally ingest into database if configured."""
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

        # Base response (always returned)
        response_data = {
            'filename': safe_name,
            'record_count': record_count,
            'warning_count': warning_count,
            'fail_count': fail_count,
            'status': 'processed'
        }

        # Check if database ingestion is explicitly enabled
        ingest_enabled = os.environ.get('HOUSEHOLDER_INGEST_ON_UPLOAD', '').lower() == 'true'
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

        if ingest_enabled and database_url:
            try:
                # Perform database ingestion
                ingestion_result = ingest_processed_csv(
                    processed_csv_path=str(processed_path),
                    original_filename=file.filename,
                    database_url=database_url,
                    uploader='system'
                )

                # Enhance response with ingestion data
                response_data.update({
                    'batch_id': ingestion_result.batch_id,
                    'ingestion_status': 'success',
                    'raw_row_count': ingestion_result.raw_row_count,
                    'validation_items_created': ingestion_result.validation_items_created,
                    'normalization_items_created': ingestion_result.normalization_items_created,
                    'duplicate_items_created': ingestion_result.duplicate_items_created,
                    'household_items_created': ingestion_result.household_items_created,
                    'audit_log_id': ingestion_result.audit_log_id
                })

                logger.info(f"Ingested batch {ingestion_result.batch_id} with {ingestion_result.raw_row_count} rows")

            except (IngestionValidationError, IngestionIOError) as e:
                # Validation error from CSV processing or file I/O
                logger.error(f"Ingestion validation error: {e}")
                return jsonify({
                    'error': f'Ingestion validation failed: {str(e)}',
                    'status': 'validation_error'
                }), 400

            except IngestionDatabaseError as e:
                # Database error during ingestion
                logger.error(f"Ingestion database error: {e}")
                return jsonify({
                    'error': f'Ingestion database error: {str(e)}',
                    'status': 'database_error'
                }), 500

            except Exception as e:
                # Unexpected error during ingestion
                logger.error(f"Unexpected ingestion error: {e}")
                return jsonify({
                    'error': f'Ingestion failed: {str(e)}',
                    'status': 'ingestion_error'
                }), 500

        return jsonify(response_data)

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
                df = pd.read_csv(f, dtype=str, encoding='utf-8').fillna('')
                record_count = len(df)
                pass_count = len(df[df['Validation_Tier'] == 'PASS'])
                warning_count = len(df[df['Validation_Tier'] == 'WARNING'])
                fail_count = len(df[df['Validation_Tier'] == 'FAIL'])

                # Count normalizations, households, duplicates from Issues/Suggested_Modifications
                normalizations_count = 0
                households_count = 0
                duplicates_count = 0

                for col in ['Issues', 'Suggested_Modifications']:
                    if col in df.columns:
                        for idx, value in df[col].items():
                            val_str = str(value).lower() if value else ''
                            if 'normaliz' in val_str or 'correct' in val_str or 'format' in val_str:
                                normalizations_count += 1
                            if 'household' in val_str or 'family' in val_str or 'address' in val_str and 'same' in val_str:
                                households_count += 1
                            if 'duplicate' in val_str:
                                duplicates_count += 1

                # Determine status based on Operator_Decision column
                decisions_made = 0
                if 'Operator_Decision' in df.columns:
                    decisions_made = len(df[df['Operator_Decision'].astype(str).str.strip() != ''])

                if decisions_made == 0:
                    status = 'Pending Review'
                elif decisions_made >= record_count:
                    status = 'Completed'
                else:
                    status = 'In Review'

                # Get upload time from filename (format: upload_YYYYMMDD_HHMMSS_*)
                try:
                    parts = f.name.split('_')
                    if len(parts) >= 3:
                        upload_time = datetime.strptime(f"{parts[1]}_{parts[2]}", '%Y%m%d_%H%M%S')
                        uploaded_str = format_relative_time(upload_time)
                    else:
                        uploaded_str = 'Unknown'
                except:
                    uploaded_str = 'Unknown'

                files.append({
                    'filename': f.name,
                    'rows': record_count,
                    'pass_count': pass_count,
                    'warning_count': warning_count,
                    'fail_count': fail_count,
                    'mtime': f.stat().st_mtime,
                    'uploaded': uploaded_str,
                    'normalizations': normalizations_count,
                    'households': households_count,
                    'duplicates': duplicates_count,
                    'status': status
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
            'date': None,
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
            if field == 'date':
                for variant in ['Date', 'Donation Date', 'donation_date']:
                    if variant in df.columns:
                        field_to_column[field] = variant
                        break
            elif field == 'name':
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

@app.route('/api/processing/<filename>/recalculate-tier', methods=['POST'])
def recalculate_tier(filename):
    """
    Recalculate validation tier for a record after edits.

    Expected JSON:
    {
        "record": {
            "Name": "John Doe",
            "Email": "john@gmail.com",
            "Phone": "5551234567",
            "Amount": "100",
            ...
        }
    }

    Returns:
    {
        "tier": "PASS|WARNING|FAIL"
    }
    """
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    try:
        data = request.get_json() or {}
        record = data.get('record', {})

        if not record:
            return jsonify({'error': 'No record provided'}), 400

        # Load configs
        rules = load_rules()
        reference = load_reference_list()

        # Build header mapping from the record keys
        # Create a minimal header_map from record keys
        header_map = build_header_mapping(record.keys())

        # Run all validations on the record - collect issues and suggestions
        validation_results = {}
        issues = []
        suggestions = []

        # Validate transaction ID (required)
        tier, reason, suggestion = validate_transaction_id(record, header_map)
        validation_results['transaction_id'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Transaction ID: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate date (required)
        tier, reason, suggestion = validate_date(record, header_map)
        validation_results['date'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Date: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate email (required)
        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        validation_results['email'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Email: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate amount (required)
        tier, reason, suggestion = validate_amount(record, header_map, reference)
        validation_results['amount'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Amount: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate name (required)
        tier, reason, suggestion = validate_name(record, header_map, reference)
        validation_results['name'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Name: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate phone (optional)
        tier, reason, suggestion = validate_phone(record, header_map, rules)
        validation_results['phone'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Phone: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate address (optional)
        tier, reason = validate_address(record, header_map)
        validation_results['address'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Address: {reason}")

        # Assign tier based on validation results
        # Always recalculate the tier from validation results when this endpoint is called
        new_tier = assign_tier(validation_results)

        # Save the edited record back to the CSV file
        try:
            path = PROCESSING_DIR / filename
            df = pd.read_csv(path, dtype=str, encoding='utf-8').fillna('')

            # Find the record index - use the first column (transaction ID) as lookup
            record_idx = None
            txn_id_col = header_map.get('transaction_id')
            if txn_id_col and txn_id_col in record:
                for idx, row in df.iterrows():
                    if str(row[txn_id_col]).strip() == str(record[txn_id_col]).strip():
                        record_idx = idx
                        break

            # If found, update all edited fields in the DataFrame
            if record_idx is not None:
                for field_key, col_name in header_map.items():
                    if col_name in record:
                        # Create column if it doesn't exist (e.g., adding phone to records without phone)
                        if col_name not in df.columns:
                            df[col_name] = ''
                        df.at[record_idx, col_name] = record[col_name]

                # Update validation columns
                df.at[record_idx, 'Validation_Tier'] = new_tier
                df.at[record_idx, 'Issues'] = "; ".join(issues) if issues else "None"
                df.at[record_idx, 'Suggested_Modifications'] = "; ".join(suggestions) if suggestions else ""

                # Update operator decision and notes if provided
                if 'Operator_Decision' in record and record['Operator_Decision']:
                    if 'Operator_Decision' not in df.columns:
                        df['Operator_Decision'] = ''
                    df.at[record_idx, 'Operator_Decision'] = record['Operator_Decision']

                if 'Operator_Notes' in record:
                    if 'Operator_Notes' not in df.columns:
                        df['Operator_Notes'] = ''
                    df.at[record_idx, 'Operator_Notes'] = record['Operator_Notes']

                # Save back to CSV
                df.to_csv(path, index=False, encoding='utf-8')
                logger.info(f"Saved edits to {filename} at index {record_idx}")
        except Exception as e:
            logger.error(f"Failed to save edits to CSV: {e}")
            # Don't fail the request, just log the error

        logger.info(f"Recalculated tier for {filename}: {new_tier}")
        return jsonify({
            'tier': new_tier,
            'issues': issues[:5],  # Limit to 5 like processor does
            'suggestions': suggestions[:5]
        })

    except Exception as e:
        logger.error(f"Error recalculating tier for {filename}: {e}")
        return jsonify({'error': f'Recalculation failed: {str(e)}'}), 500


@app.route('/api/processing/<filename>/refresh-validation', methods=['POST'])
@require_auth
def refresh_validation(filename):
    """Re-run validation on existing processing file to regenerate issues/suggestions."""
    if not validate_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    processing_path = PROCESSING_DIR / filename
    try:
        # Read the original data (before decisions were made)
        df = pd.read_csv(processing_path, dtype=str, encoding='utf-8').fillna('')

        # Preserve operator decisions and notes
        decisions = df['Operator_Decision'].to_dict() if 'Operator_Decision' in df.columns else {}
        notes = df['Operator_Notes'].to_dict() if 'Operator_Notes' in df.columns else {}

        # Create temporary file with just the data columns (no validation columns)
        temp_df = df.drop(columns=['Validation_Tier', 'Issues', 'Suggested_Modifications',
                                    'Operator_Decision', 'Operator_Notes'], errors='ignore')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_input:
            temp_df.to_csv(temp_input.name, index=False, encoding='utf-8')
            temp_input_path = temp_input.name

        # Re-run processor
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_output:
            temp_output_path = temp_output.name

        run_processor(temp_input_path, temp_output_path)

        # Read revalidated data
        df_revalidated = pd.read_csv(temp_output_path, dtype=str, encoding='utf-8').fillna('')

        # Restore operator decisions and notes
        if 'Operator_Decision' in df.columns:
            df_revalidated['Operator_Decision'] = df_revalidated.index.map(
                lambda idx: decisions.get(idx, '')
            )
        if 'Operator_Notes' in df.columns:
            df_revalidated['Operator_Notes'] = df_revalidated.index.map(
                lambda idx: notes.get(idx, '')
            )

        # Save back to processing file
        df_revalidated.to_csv(processing_path, index=False, encoding='utf-8')

        logger.info(f"Refreshed validation for {filename}")

        # Cleanup temp files
        Path(temp_input_path).unlink(missing_ok=True)
        Path(temp_output_path).unlink(missing_ok=True)

        return jsonify({
            'status': 'refreshed',
            'message': f'Validation refreshed for {filename}. Reload the page to see updated issues/suggestions.'
        })
    except Exception as e:
        logger.error(f"Error refreshing validation for {filename}: {e}")
        return jsonify({'error': f'Refresh failed: {str(e)}'}), 500


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

@app.route('/test-override-dialog')
def test_override_dialog():
    """Test endpoint that serves review page with pre-populated FAIL records.

    Used for E2E testing of override confirmation dialog without upload complexity.
    """
    # Create test CSV with FAIL tier records
    test_data = {
        'Donation ID': ['GB001', 'GB002', 'GB003', 'GB004'],
        'Date': ['2026-06-01', '2026-06-01', '2026-06-01', '2026-06-01'],
        'Name': ['John Smith', 'Jane Doe', 'Bob Wilson', 'Alice Brown'],
        'Email': ['john@gmail.com', '', 'bob@example.com', 'alice@test.com'],
        'Phone': ['5551234567', '5559876543', '5551112222', ''],
        'Amount': ['100', '250', '', '0'],
        'Campaign': ['Annual Giving', 'Annual Giving', 'Campaign X', 'Campaign X']
    }

    df = pd.DataFrame(test_data)

    # Run validation to get tiers
    from processor import process_csv
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as input_f:
        df.to_csv(input_f.name, index=False)
        input_path = input_f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as output_f:
        output_path = output_f.name

    try:
        process_csv(input_path, output_path)
        result_df = pd.read_csv(output_path, dtype=str)

        # Convert to records for rendering
        records = []
        for idx, row in result_df.iterrows():
            record = row.to_dict()
            record['idx'] = int(idx)
            records.append(record)

        # Render review template with test records
        return render_template('review.html',
                             test_mode=True,
                             records=records,
                             filename='test_override_records.csv')
    except Exception as e:
        logger.error(f"Error in test override dialog: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DonorTrust v1 Phase 0 Prototype Routes — Fixture-backed, no persistence
# ============================================================================

@app.route('/imports')
def imports_list():
    """List all imports with status through service boundary."""
    imports = import_service.get_imports()
    return render_template('imports/list.html', imports=imports)

@app.route('/imports/<import_id>/dashboard')
def import_dashboard(import_id):
    """Import dashboard with queue navigation."""
    dashboard_data = dashboard_service.get_import_dashboard(import_id)
    return render_template('imports/dashboard.html',
                         batch=dashboard_data['batch'],
                         queue_status=dashboard_data['queue_status'])

@app.route('/imports/<import_id>/duplicates')
def import_duplicates(import_id):
    """Possible duplicates review."""
    data = duplicates_service.get_duplicates_review(import_id)
    return render_template('imports/duplicates.html', **data)

@app.route('/imports/<import_id>/validation')
def import_validation(import_id):
    """Validation review for records with issues."""
    data = validation_service.get_validation_review(import_id)
    return render_template('imports/validation.html', **data)

@app.route('/imports/<import_id>/validation/<int:review_item_id>/decision', methods=['POST'])
def record_validation_decision(import_id, review_item_id):
    """Record a reviewer's validation decision."""
    decision = request.form.get('decision', '').strip()
    notes = request.form.get('notes', '').strip() or None
    reviewer = request.headers.get('X-Reviewer-ID') or None

    try:
        result = validation_decision_service.record_validation_decision(
            import_id=import_id,
            review_item_id=review_item_id,
            decision=decision,
            notes=notes,
            reviewer=reviewer,
        )
        logger.info(f"Validation decision recorded: {result.decision} for item {review_item_id}")
        return redirect(f'/imports/{import_id}/validation')
    except ValueError as e:
        logger.warning(f"Validation error recording decision: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error recording validation decision: {str(e)}")
        return jsonify({'error': 'Error recording decision'}), 500

@app.route('/imports/<import_id>/normalizations')
def import_normalizations(import_id):
    """Field normalization suggestions."""
    data = normalizations_service.get_normalizations_review(import_id)
    return render_template('imports/normalizations.html', **data)

@app.route('/imports/<import_id>/normalizations/<int:review_item_id>/decision', methods=['POST'])
def record_normalization_decision(import_id, review_item_id):
    """Record a reviewer's normalization decision."""
    from scripts.householder import normalization_decision_service

    decision = request.form.get('decision', '').strip()
    notes = request.form.get('notes', '').strip() or None
    reviewer = request.headers.get('X-Reviewer-ID') or None

    try:
        result = normalization_decision_service.record_normalization_decision(
            import_id=import_id,
            review_item_id=review_item_id,
            decision=decision,
            notes=notes,
            reviewer=reviewer,
        )
        logger.info(f"Normalization decision recorded: {result.decision} for item {review_item_id}")
        return redirect(f'/imports/{import_id}/normalizations')
    except ValueError as e:
        logger.warning(f"Validation error recording normalization decision: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error recording normalization decision: {str(e)}")
        return jsonify({'error': 'Error recording decision'}), 500

@app.route('/imports/<import_id>/duplicates/<int:review_item_id>/decision', methods=['POST'])
def record_duplicate_decision(import_id, review_item_id):
    """Record a reviewer's duplicate decision."""
    from scripts.householder import duplicate_decision_service

    decision = request.form.get('decision', '').strip()
    notes = request.form.get('notes', '').strip() or None
    reviewer = request.headers.get('X-Reviewer-ID') or None

    try:
        result = duplicate_decision_service.record_duplicate_decision(
            import_id=import_id,
            review_item_id=review_item_id,
            decision=decision,
            notes=notes,
            reviewer=reviewer,
        )
        logger.info(f"Duplicate decision recorded: {result.decision} for item {review_item_id}")
        return redirect(f'/imports/{import_id}/duplicates')
    except ValueError as e:
        logger.warning(f"Validation error recording duplicate decision: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error recording duplicate decision: {str(e)}")
        return jsonify({'error': 'Error recording decision'}), 500

@app.route('/imports/<import_id>/households/<int:review_item_id>/decision', methods=['POST'])
def record_household_decision(import_id, review_item_id):
    """Record a reviewer's household decision."""
    from scripts.householder import household_decision_service

    decision = request.form.get('decision', '').strip()
    notes = request.form.get('notes', '').strip() or None
    reviewer = request.headers.get('X-Reviewer-ID') or None

    try:
        result = household_decision_service.record_household_decision(
            import_id=import_id,
            review_item_id=review_item_id,
            decision=decision,
            notes=notes,
            reviewer=reviewer,
        )
        logger.info(f"Household decision recorded: {result.decision} for item {review_item_id}")
        return redirect(f'/imports/{import_id}/households')
    except ValueError as e:
        logger.warning(f"Validation error recording household decision: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error recording household decision: {str(e)}")
        return jsonify({'error': 'Error recording decision'}), 500

@app.route('/imports/<import_id>/households')
def import_households(import_id):
    """Household grouping confirmation."""
    data = households_service.get_households_review(import_id)
    return render_template('imports/households.html', **data)

@app.route('/imports/<import_id>/audit')
def import_audit(import_id):
    """Audit log for all reviewer decisions."""
    data = audit_service.get_audit_log(import_id)
    return render_template('imports/audit.html', **data)

@app.route('/imports/<import_id>/exports')
def import_exports(import_id):
    """Export console for generating and downloading exports."""
    data = exports_service.get_export_console(import_id)
    return render_template('imports/exports.html', **data)

@app.route('/imports/<import_id>/exports/preview', methods=['POST'])
def preview_export(import_id):
    """Generate export preview based on reviewer decisions."""
    from scripts.householder import export_preview_service

    try:
        preview = export_preview_service.build_export_preview(import_id)
        logger.info(f"Export preview generated: {preview.row_count} rows, {preview.blocked_count} blocked")

        # Return preview data in template context
        data = exports_service.get_export_console(import_id)
        data['preview'] = preview.to_template_dict()
        data['preview_available'] = True

        return render_template('imports/exports.html', **data)
    except ValueError as e:
        logger.warning(f"Export preview error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error generating export preview: {str(e)}")
        return jsonify({'error': 'Error generating preview'}), 500


@app.route('/imports/<import_id>/exports/generate', methods=['POST'])
def generate_export(import_id):
    """Explicitly generate export file from approved preview."""
    from scripts.householder import export_file_service

    try:
        reviewer = request.headers.get('X-Reviewer-ID')
        output_dir = current_app.config.get('EXPORT_OUTPUT_DIR', '/tmp/givebutter/exports')

        result = export_file_service.generate_export_file(
            import_id=import_id,
            output_dir=output_dir,
            reviewer=reviewer,
        )

        logger.info(f"Export file generated: {import_id} -> {result.filename}")

        return jsonify({
            "status": "success",
            "file": result.to_dict()
        }), 200

    except export_file_service.ExportBlockedError as e:
        logger.warning(f"Export blocked for {import_id}: {e.message}")
        return jsonify({
            "status": "blocked",
            "error": e.message,
            "blockers": e.blockers,
            "blocked_count": e.blocked_count
        }), 400

    except ValueError as e:
        logger.warning(f"Export validation error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

    except export_file_service.ExportError as e:
        logger.error(f"Export error for {import_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Failed to generate export: {str(e)}"
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error generating export: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Error generating export"
        }), 500


@app.route('/imports/<import_id>/exports/download/<int:audit_log_id>')
def download_export(import_id, audit_log_id):
    """Download previously generated export file."""
    from scripts.householder import export_download_service

    try:
        output_dir = current_app.config.get('EXPORT_OUTPUT_DIR', '/tmp/givebutter/exports')

        download_info = export_download_service.get_export_download_info(
            import_id=import_id,
            audit_log_id=audit_log_id,
            export_dir=output_dir,
        )

        logger.info(f"Export download: {import_id} audit={audit_log_id} file={download_info.filename}")

        return send_file(
            download_info.file_path,
            as_attachment=True,
            download_name=download_info.filename,
            mimetype=download_info.content_type,
        )

    except export_download_service.ExportNotFoundError as e:
        logger.warning(f"Export not found: {import_id} audit={audit_log_id}")
        return jsonify({"error": "Export not found"}), 404

    except export_download_service.ExportAccessError as e:
        logger.warning(f"Access denied for export: {import_id} audit={audit_log_id}")
        return jsonify({"error": "Access denied"}), 403

    except export_download_service.ExportPathError as e:
        logger.warning(f"Path error for export: {import_id} audit={audit_log_id}")
        return jsonify({"error": "File not found"}), 404

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({"error": "Download failed"}), 500


@app.route('/health')
def health():
    return jsonify({"status": "ok", "version": "3.0"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
