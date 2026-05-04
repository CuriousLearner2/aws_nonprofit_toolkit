# Compliance & Data Privacy Roadmap

This document outlines the security measures and compliance standards followed by the Replate Growth Lab for both synthetic and production data.

---

## 1. Meta API Compliance
Even in a sandbox/test environment, the following rules are strictly enforced to align with Meta’s Terms of Service.

### 1.1 Data Hashing (Privacy-by-Design)
*   **Requirement**: Meta requires all personally identifiable information (PII) to be SHA256 hashed before transmission.
*   **Implementation**: The `hash_data()` function in `meta_growth_engine.py` hashes emails locally before they ever hit the network.
*   **Production Safeguard**: Raw email addresses are **never** logged or stored in the Meta Custom Audience object.

### 1.2 Consent Management
*   **Synthetic Logic**: Our generation scripts include a `CONSENT` flag.
*   **Filtering**: The marketing scripts are designed to filter out any user where `CONSENT == False`.
*   **Production Safeguard**: In a live environment, this flag would be synchronized with our production database's "Marketing Opt-In" status.

---

## 2. Security Best Practices (Hardening)

### 2.1 Credential Protection
*   **No Hardcoding**: API tokens (Gemini, Meta) and Account IDs are stored in `.env` files and accessed via `os.getenv()`.
*   **Sanitized Logging**: All `print()` and `logger` statements have been audited to ensure they do not output full API tokens or long-lived session IDs.
*   **Git Protection**: All `.env` and `.log` files are included in `.gitignore` to prevent accidental exposure to GitHub.

---

## 3. Production Readiness Checklist
Before moving from synthetic simulations to real donor data, the following steps are required:

1.  **PII Audit**: Final verification that no raw PII (Phone, Email, Name) is leaked in logs or error traces.
2.  **Access Rotation**: Rotate all sandbox tokens and replace them with production-scoped tokens (with limited permissions).
3.  **Data Retention Policy**: Implement the automated masking of `donor_whatsapp_id` after 30 days, as documented in the [Architecture Overview](../replate/ARCHITECTURE.md).
4.  **Legal Review**: Ensure the donor-facing WhatsApp bot includes a clear Privacy Policy link and an "Opt-Out" (STOP/CANCEL) mechanism.
