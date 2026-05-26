# Changelog

## v2.3 - 2026-05-24
- Added exception handling for parse errors
- Implemented full 11-test suite
- Added household matching logic (email > phone > address)
- Added simple upload form
- Moved to human-in-the-loop remediation model

## Planned v2.4 - Human-Approved Config UX
**Note:** Current v2.3 requires humans to manually edit `config/rules_v2.3.json`.

Next version will add a review UI so humans never touch JSON directly:
- Claude's "Remediation proposed" email will include a link to `/review/{escalation_id}`
- UI shows: what is wrong, proposed JSON diff, test results
- Human clicks "Approve" → system writes new `rules_v2.4.json`, bumps version, and auto-requeues the original file
- Human clicks "Reject" → escalation stays in human_review with comment
- Audit log captures who approved and when

This preserves human control while removing direct config file editing.
