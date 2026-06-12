"""
Export Console Configuration - Static application metadata.

Defines the available export options that are shown in the export console.
This is static application configuration shared by all repositories.

Phase 1B: Metadata only. Export cards define available export formats.
No file generation, no database schema dependency.
"""

# Static export card definitions - application-level configuration
# These define the 4 export options available in the export console
EXPORT_CARD_DEFINITIONS = [
    {
        'id': 'EXPORT-REVIEWED',
        'name': 'Reviewed Export',
        'status': 'Generated',
        'description': 'CSV reflecting reviewer-confirmed duplicate decisions and household groupings in export staging',
        'files_ready': 1,
    },
    {
        'id': 'EXPORT-HOUSEHOLD',
        'name': 'Household Export',
        'status': 'Ready',
        'description': 'Confirmed household groupings with member composition',
        'files_ready': 1,
    },
    {
        'id': 'EXPORT-BACKLOG',
        'name': 'Backlog Export',
        'status': 'Pending Review',
        'description': 'Records with unresolved suggestions or pending reviewer decisions',
        'files_ready': 0,
    },
    {
        'id': 'EXPORT-RAW',
        'name': 'Raw Export',
        'status': 'Ready',
        'description': 'Original data unchanged; no reviewer modifications',
        'files_ready': 1,
    },
]
