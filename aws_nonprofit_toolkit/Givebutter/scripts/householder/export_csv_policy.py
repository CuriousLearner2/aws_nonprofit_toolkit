"""Pure CSV serialization policy for export rows."""

import csv
from io import StringIO
from typing import Any


_EXPORT_HEADER = (
    'source_row_index', 'transaction_id', 'first_name', 'last_name', 'email', 'phone',
    'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'amount',
    'validation_status', 'validation_issues', 'normalized_fields', 'normalization_warnings',
    'duplicate_group_id', 'duplicate_decision', 'duplicate_warnings',
    'household_group_id', 'household_group_label', 'household_members', 'household_decision', 'household_warnings',
    'export_warnings'
)


def encode_csv_field(value: Any) -> str:
    """Encode one export value using the stable CSV field policy."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ";".join(str(item) for item in value if item is not None)
    return str(value)


def generate_csv_content(export_rows: tuple) -> str:
    """Serialize export rows with the stable header and field order."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(_EXPORT_HEADER)
    for row in export_rows:
        writer.writerow([
            encode_csv_field(row.source_row_index),
            encode_csv_field(row.transaction_id),
            encode_csv_field(row.first_name),
            encode_csv_field(row.last_name),
            encode_csv_field(row.email),
            encode_csv_field(row.phone),
            encode_csv_field(row.address_line1),
            encode_csv_field(row.address_line2),
            encode_csv_field(row.city),
            encode_csv_field(row.state),
            encode_csv_field(row.postal_code),
            encode_csv_field(row.amount),
            encode_csv_field(row.validation_status),
            encode_csv_field(row.validation_issues),
            encode_csv_field(row.normalized_fields),
            encode_csv_field(row.normalization_warnings),
            encode_csv_field(row.duplicate_group_id),
            encode_csv_field(row.duplicate_decision),
            encode_csv_field(row.duplicate_warnings),
            encode_csv_field(row.household_group_id),
            encode_csv_field(row.household_group_label),
            encode_csv_field(row.household_members),
            encode_csv_field(row.household_decision),
            encode_csv_field(row.household_warnings),
            encode_csv_field(row.export_warnings),
        ])
    return output.getvalue()
