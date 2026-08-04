"""Database implementations of the four item-level decision writers."""

import json
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .database_models import ReviewItem
from .decision_write_coordinator import DecisionPreparation, record_item_decision
from .write_repository_contracts import (
    ValidationDecisionResult, NormalizationDecisionResult,
    DuplicateDecisionResult, HouseholdDecisionResult,
)


def get_db_session(database_url: str = 'sqlite:///./givebutter.db') -> Session:
    engine = create_engine(database_url, echo=False)
    return sessionmaker(bind=engine)()


class DatabaseValidationDecisionWriter:
    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        self.database_url = database_url

    def create_validation_decision(
        self, batch_id: str, review_item_id: int, decision: str,
        notes: Optional[str] = None, reviewed_values: Optional[dict] = None,
        reviewer: Optional[str] = None,
    ) -> ValidationDecisionResult:
        stored_values = reviewed_values.copy() if reviewed_values else {}
        if notes:
            stored_values['notes'] = notes

        def prepare(_item: ReviewItem) -> DecisionPreparation:
            effective = {'accept_issue': 'accepted', 'dismiss_issue': 'dismissed', 'defer': 'deferred'}.get(decision, 'pending')
            return DecisionPreparation(
                reviewed_values=stored_values or None,
                audit_details={
                    'decision_type': 'validation_decision', 'decision_value': decision,
                    'notes': notes, 'reviewed_values': reviewed_values,
                },
                effective_status=effective,
            )

        return record_item_decision(
            lambda: get_db_session(self.database_url), batch_id=batch_id,
            review_item_id=review_item_id, decision=decision, reviewer=reviewer,
            item_type='validation', decision_type='validation_decision',
            status_map={'accept_issue': 'accepted', 'dismiss_issue': 'dismissed', 'defer': 'deferred'},
            result_type=ValidationDecisionResult, error_label='validation', prepare=prepare,
        )


class DatabaseNormalizationDecisionWriter:
    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        self.database_url = database_url

    def create_normalization_decision(
        self, batch_id: str, review_item_id: int, decision: str,
        notes: Optional[str] = None, reviewer: Optional[str] = None,
    ) -> NormalizationDecisionResult:
        def prepare(item: ReviewItem) -> DecisionPreparation:
            payload = item.payload_json
            if not isinstance(payload, dict):
                payload = json.loads(payload) if isinstance(payload, str) else {}
            field_name = payload.get('field')
            raw_value = payload.get('raw_value')
            normalized_value = payload.get('normalized_value')
            if not all([field_name, raw_value is not None, normalized_value is not None]):
                raise ValueError('Normalization payload missing field/raw_value/normalized_value')
            reviewed = {'field': field_name, 'raw_value': raw_value, 'normalized_value': normalized_value}
            if notes:
                reviewed['notes'] = notes
            effective = {'accept_normalization': 'accepted', 'reject_normalization': 'rejected', 'defer': 'deferred'}.get(decision, 'pending')
            return DecisionPreparation(
                reviewed_values=reviewed,
                audit_details={
                    'decision_type': 'normalization_decision', 'decision_value': decision,
                    'field': field_name, 'raw_value': raw_value,
                    'normalized_value': normalized_value, 'notes': notes,
                },
                effective_status=effective,
            )

        return record_item_decision(
            lambda: get_db_session(self.database_url), batch_id=batch_id,
            review_item_id=review_item_id, decision=decision, reviewer=reviewer,
            item_type='normalization', decision_type='normalization_decision',
            status_map={'accept_normalization': 'accepted', 'reject_normalization': 'rejected', 'defer': 'deferred'},
            result_type=NormalizationDecisionResult, error_label='normalization', prepare=prepare,
        )


class DatabaseDuplicateDecisionWriter:
    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        self.database_url = database_url

    def create_duplicate_decision(
        self, batch_id: str, review_item_id: int, decision: str,
        notes: Optional[str] = None, reviewer: Optional[str] = None,
    ) -> DuplicateDecisionResult:
        def prepare(item: ReviewItem) -> DecisionPreparation:
            payload = item.payload_json
            if not isinstance(payload, dict):
                payload = json.loads(payload) if isinstance(payload, str) else {}
            contact_a = payload.get('contact_a', {})
            contact_b = payload.get('contact_b', {})
            supporting = payload.get('supporting_evidence', [])
            conflicting = payload.get('conflicting_evidence', [])
            secondary = [contact_b.get('id')] if contact_b.get('id') else []
            candidates = [contact_a.get('id'), contact_b.get('id')] if contact_a.get('id') and contact_b.get('id') else []
            supporting = supporting if isinstance(supporting, list) else []
            conflicting = conflicting if isinstance(conflicting, list) else []
            reviewed = {
                'primary_contact_id': contact_a.get('id'), 'secondary_contact_ids': secondary,
                'candidate_contact_ids': candidates, 'evidence_supporting': supporting,
                'evidence_conflicting': conflicting,
            }
            if notes:
                reviewed['notes'] = notes
            effective = {'same_person': 'same_person', 'different_people': 'different_people', 'defer': 'deferred'}.get(decision, 'pending')
            details = {
                'decision_type': 'duplicate_decision', 'decision_value': decision,
                'primary_contact_id': contact_a.get('id'), 'secondary_contact_ids': secondary,
                'candidate_contact_ids': candidates, 'evidence_supporting': supporting,
                'evidence_conflicting': conflicting, 'notes': notes,
            }
            return DecisionPreparation(
                reviewed_values=reviewed, audit_details=details, effective_status=effective,
                mutate_item=lambda current: setattr(current, 'status', 'decided'),
            )

        return record_item_decision(
            lambda: get_db_session(self.database_url), batch_id=batch_id,
            review_item_id=review_item_id, decision=decision, reviewer=reviewer,
            item_type='duplicate', decision_type='duplicate_decision',
            status_map={'same_person': 'same_person', 'different_people': 'different_people', 'defer': 'deferred'},
            result_type=DuplicateDecisionResult, error_label='duplicate', prepare=prepare,
        )


class DatabaseHouseholdDecisionWriter:
    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        self.database_url = database_url

    def create_household_decision(
        self, batch_id: str, review_item_id: int, decision: str,
        notes: Optional[str] = None, reviewer: Optional[str] = None,
    ) -> HouseholdDecisionResult:
        def prepare(item: ReviewItem) -> DecisionPreparation:
            payload = item.payload_json
            if not isinstance(payload, dict):
                payload = json.loads(payload) if isinstance(payload, str) else {}
            household_id = payload.get('id')
            label = payload.get('suggested_name')
            address = payload.get('address')
            basis = payload.get('evidence', [])
            members = payload.get('proposed_members', [])
            member_count = len(members) if isinstance(members, list) else 0
            candidate_ids = []
            if isinstance(members, list):
                for member in members:
                    if isinstance(member, str):
                        match = re.search(r'\(([^)]+)\)', member)
                        if match:
                            candidate_ids.append(match.group(1))
            basis = basis if isinstance(basis, list) else []
            reviewed = {
                'candidate_household_id': household_id, 'candidate_contact_ids': candidate_ids,
                'suggested_household_label': label, 'address': address, 'basis': basis,
                'proposed_members_count': member_count,
            }
            if notes:
                reviewed['notes'] = notes
            effective = {'confirm_household': 'confirmed', 'reject_household': 'rejected', 'defer': 'deferred'}.get(decision, 'pending')
            return DecisionPreparation(
                reviewed_values=reviewed,
                audit_details={
                    'decision_type': 'household_decision', 'decision_value': decision,
                    'candidate_household_id': household_id, 'candidate_contact_ids': candidate_ids,
                    'suggested_household_label': label, 'address': address, 'basis': basis,
                    'proposed_members_count': member_count, 'notes': notes,
                },
                effective_status=effective,
            )

        return record_item_decision(
            lambda: get_db_session(self.database_url), batch_id=batch_id,
            review_item_id=review_item_id, decision=decision, reviewer=reviewer,
            item_type='household', decision_type='household_decision',
            status_map={'confirm_household': 'confirmed', 'reject_household': 'rejected', 'defer': 'deferred'},
            result_type=HouseholdDecisionResult, error_label='household', prepare=prepare,
        )
