"""
Database Models for DonorTrust Householder v1 - Phase 1B (Option C: Extensible Review-Items)

SQLAlchemy declarative models for import batch processing.
All tables are append-only (immutable after creation) except review_decisions.

Design principles:
- Raw import rows are immutable (append-only)
- Import contact snapshots are immutable (denormalized for query efficiency)
- Review items are polymorphic suggestions (immutable after creation)
- Review item subjects enable flexible entity references (current import rows now, existing records later)
- Review decisions are append-only (decisions accumulate, never modified)
- Audit log is append-only (immutable record of actions)

Polymorphic Subject References (enable future match domain without global master-person design):
- Phase 1B subject_type values: 'import_raw_row', 'import_contact_snapshot'
- Future subject_type values (Phase 2+, not implemented yet): 'prior_import_row', 'prior_import_contact', 'existing_contact', 'existing_household'

All models use pure SQLAlchemy (no Flask-SQLAlchemy coupling).
Database session management is isolated from models.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class ImportBatch(Base):
    """Import batch metadata and status."""
    __tablename__ = 'import_batches'

    id = Column(String(50), primary_key=True)
    filename = Column(String(255), nullable=False)
    upload_timestamp = Column(DateTime, nullable=False)
    uploader = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default='pending')
    raw_row_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ImportBatch {self.id}>'


class RawImportRow(Base):
    """Raw CSV row data - immutable after creation."""
    __tablename__ = 'raw_import_rows'

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(50), ForeignKey('import_batches.id'), nullable=False)
    row_index = Column(Integer, nullable=False)
    raw_csv_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<RawImportRow {self.id} batch={self.batch_id}>'


class ImportContact(Base):
    """Denormalized contact snapshot - immutable after creation."""
    __tablename__ = 'import_contacts'

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(50), ForeignKey('import_batches.id'), nullable=False)
    raw_import_row_id = Column(Integer, ForeignKey('raw_import_rows.id'), nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(10), nullable=True)
    postal_code = Column(String(20), nullable=True)
    amount = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ImportContact {self.id} {self.first_name} {self.last_name}>'


class ReviewItem(Base):
    """Polymorphic review item (suggestion/finding) - immutable after creation.

    Replaces typed tables (NormalizationSuggestion, DuplicateCandidateRecord, HouseholdSuggestion).

    item_type values:
    - 'validation': data validation issue needing human review
    - 'normalization': field value that could be standardized
    - 'duplicate': potential duplicate record (within import or against existing)
    - 'household': potential household grouping

    payload_json varies by item_type:
    - normalization: {field_name, raw_value, normalized_value, confidence, basis}
    - duplicate: {match_type, evidence[], conflicts[], confidence}
    - household: {suggested_label, basis, confidence}

    Phase 1B: items reference only current import rows via review_item_subjects.
    Phase 2+: items can reference prior imports or existing records (no schema change needed).
    """
    __tablename__ = 'review_items'

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(50), ForeignKey('import_batches.id'), nullable=False)
    item_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    payload_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ReviewItem {self.id} type={self.item_type}>'


class ReviewItemSubject(Base):
    """Polymorphic subject reference for a review item.

    Enables flexible entity references without global master tables.

    Phase 1B subject_type values:
    - 'import_raw_row': references raw_import_rows.id
    - 'import_contact_snapshot': references import_contacts.id

    Future subject_type values (Phase 2+, not implemented yet):
    - 'prior_import_row': references prior raw_import_rows (from archive)
    - 'prior_import_contact': references prior import_contacts (from archive)
    - 'existing_contact': references existing_contacts table (when added)
    - 'existing_household': references existing_households table (when added)

    role examples: 'primary', 'secondary', 'member', 'existing_match', etc.
    """
    __tablename__ = 'review_item_subjects'

    id = Column(Integer, primary_key=True)
    review_item_id = Column(Integer, ForeignKey('review_items.id'), nullable=False)
    subject_type = Column(String(50), nullable=False)
    subject_id = Column(Integer, nullable=False)
    role = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ReviewItemSubject {self.id} type={self.subject_type} id={self.subject_id}>'


class ReviewDecision(Base):
    """Review decision recorded by reviewer - append-only.

    Each decision applies to a review_item as a whole.
    One item may have multiple subjects; the decision treats them as a unit.

    decision values: 'accept', 'reject', 'same_person', 'different_person', 'defer', 'confirmed'
    """
    __tablename__ = 'review_decisions'

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(50), ForeignKey('import_batches.id'), nullable=False)
    review_item_id = Column(Integer, ForeignKey('review_items.id'), nullable=False)
    decision = Column(String(100), nullable=False)
    reviewed_values = Column(JSON, nullable=True)
    reviewer = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ReviewDecision {self.id} item={self.review_item_id} decision={self.decision}>'


class AuditLogRecord(Base):
    """Audit log entry - immutable record of reviewer actions.

    action_type examples: 'item_created', 'decision_recorded', 'batch_imported'
    """
    __tablename__ = 'audit_log'

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(50), ForeignKey('import_batches.id'), nullable=False)
    action_type = Column(String(100), nullable=False)
    action_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    actor = Column(String(255), nullable=True)
    item_id = Column(Integer, ForeignKey('review_items.id'), nullable=True)
    decision_id = Column(Integer, ForeignKey('review_decisions.id'), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLogRecord {self.id} {self.action_type}>'


# Database initialization helpers
def create_db_engine(database_url: str = None):
    """
    Create SQLAlchemy engine.

    Args:
        database_url: Database connection string.
                     Defaults to SQLite in current directory for testing.

    Returns:
        SQLAlchemy Engine instance
    """
    if database_url is None:
        database_url = 'sqlite:///./givebutter.db'

    engine = create_engine(database_url, echo=False)
    return engine


def init_db(database_url: str = None):
    """
    Initialize database schema.

    Creates all tables defined in Base.metadata.
    Safe to call multiple times (creates tables if not exist).

    Args:
        database_url: Database connection string (optional)
    """
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """
    Get new database session.

    Args:
        engine: SQLAlchemy engine

    Returns:
        SQLAlchemy Session instance
    """
    Session = sessionmaker(bind=engine)
    return Session()
