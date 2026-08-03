"""Policy for normalizing validation issue payloads used by export preview."""


def validation_issue_type(payload):
    if not payload:
        return "unknown"
    return payload.get("issue", payload.get("issue_type", "unknown"))


def validation_issue_field(payload, issue_type=None):
    if not payload:
        return None
    field = payload.get("field")
    if field:
        return str(field).strip().lower()
    issue_type_lower = str(issue_type or "").lower()
    for candidate in ("date", "amount", "email", "phone"):
        if candidate in issue_type_lower:
            return candidate
    return None
