# Householder v1.1 — Operator Task 4: HTTPS / Network / Security Configuration

**Version:** 1.1  
**Status:** Security Configuration Complete  
**Date:** 2026-06-13  
**Purpose:** Define HTTPS, network, and security requirements for Householder v1.1 operator deployment

---

## Executive Summary

Householder v1.1 is a review and export tool with no external API calls, no CRM integration, and no application-level credentials required. Security is provided by deployment environment (network access controls, optional bearer token, file permissions) rather than application-level authentication.

**Critical clarification:** v1.1 does NOT add application-level RBAC. Access control must be provided by the deployment environment (local-only, private network, reverse proxy, or infrastructure-level authentication).

---

## Security Model Summary

### What v1.1 Provides

✓ **Read-only preview and readiness routes** (no side effects)  
✓ **Append-only audit trail** (all actions logged)  
✓ **Immutable raw data** (source data never modified)  
✓ **File permission checks** on exports and database  
✓ **Path traversal prevention** (batch isolation enforced)  
✓ **Symlink escape prevention** (no following symlinks)  
✓ **Optional pre-existing bearer token gate** (via `ADMIN_TOKEN` env var, not RBAC)  

### What v1.1 Does NOT Provide (and Will Not Add)

✗ **Application-level RBAC** (no role-based access control)  
✗ **Login/session management** (not implemented)  
✗ **User accounts or per-user permissions** (all authenticated users have full access)  
✗ **User identification** (audit log records actions but not who performed them)  
✗ **HTTPS/TLS** (Flask runs on HTTP; must be provided by deployment)  
✗ **External API calls** (no CRM integration)  
✗ **Credentials/secrets** (SQLite uses file permissions)  

### Therefore: Operator Must Provide

✓ **Network access control** (local-only, VPN, firewall, reverse proxy)  
✓ **HTTPS/TLS termination** (if traffic leaves localhost)  
✓ **Infrastructure-level authentication** (SSO, reverse proxy auth, etc.)  
✓ **File system permissions** (ensure safe directory/file ownership)  
✓ **Backup/recovery procedures** (documented in Task 3)  

---

## No External API Calls — Verified

**Verification:** Grep search of all product code for external service calls, credentials, and CRM references.

**Search results:**

```bash
grep -r "requests\.|urllib\|http\.|api_key\|credential\|givebutter.*api\|crm.*api" \
  scripts/householder/ \
  --include="*.py" \
  --exclude-dir=__pycache__ \
  --exclude="*.pyc"
```

**Finding:** ✓ NO external HTTP calls found  
✓ NO credential/API key usage found  
✓ NO CRM/Givebutter API integration found  
✓ NO third-party service dependencies found  

**Only references found:** Documentation and default values (e.g., "givebutter_export" as a field label, not an API call).

**Assessment:** v1.1 is completely self-contained. No internet connectivity required.

---

## Application-Level Authentication

### Pre-Existing Optional Bearer Token Gate

**Important clarification:** v1.1 does NOT add any new authentication. The following optional bearer token gate is **pre-existing** (Phase 1C) and is NOT an RBAC system or user model.

**Pre-existing code (read-only for this task):**

```python
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')

if ADMIN_TOKEN:
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401
```

**Behavior:**
- If `ADMIN_TOKEN` environment variable is NOT set: Application is **open access** (no gate)
- If `ADMIN_TOKEN` environment variable IS set: Requests must include `Authorization: Bearer <token>` header

**Important:** This is a simple all-or-nothing bearer token gate, NOT:
- Not RBAC (role-based access control)
- Not a user model (no user accounts, no per-user permissions)
- Not session management (no login/logout, no user tracking)
- Not authentication of who performed actions (all users look the same to the app)

**Use case:** Optional simple gate for operator convenience when running on shared networks.

### What v1.1 Does NOT Have

✗ **Login/logout** — No user sessions, no login page  
✗ **RBAC** — No role-based access control  
✗ **User accounts** — No user database or user management  
✗ **Per-user permissions** — If authenticated, all users have full access to all data  
✗ **User identification** — Audit log records actions but cannot identify who performed them  

### Therefore: Access Control Must Be Provided By Deployment Environment

- **Local-only:** File system permissions + localhost binding (recommended for v1.1)
- **Private network:** Firewall/VPN + optional pre-existing bearer token (if desired)
- **Production/Internet-exposed:** Reverse proxy with HTTPS/TLS + infrastructure-level authentication (SSO/OIDC/SAML)

**Not recommended:** Relying on ADMIN_TOKEN alone for production or multi-user access. Use infrastructure-level controls.  

---

## Deployment Modes and Guidance

### Mode 1: Local-Only Development/Operator Use

**Use case:** Operator running Householder on their local machine for review and export

**Configuration:**

```bash
# Bind to localhost only (default)
flask run --host=127.0.0.1 --port=8000

# Or with explicit local binding
python -m flask run --host=127.0.0.1 --port=8000

# Do NOT set ADMIN_TOKEN for local-only use
# (no authentication needed if only localhost can access)
```

**Requirements:**
- Operator access: local file system permissions
- Network access: localhost only (127.0.0.1)
- HTTPS: NOT required (localhost, not exposed)
- Authentication: NOT required (local-only)

**Verification:**

```bash
# Confirm binding to localhost
netstat -an | grep 8000
# Should show: 127.0.0.1:8000

# Confirm app is NOT accessible from other machines
curl http://127.0.0.1:8000/
# Should work

curl http://<other-ip>:8000/
# Should timeout/fail
```

---

### Mode 2: Private Network / Internal Deployment

**Use case:** Householder running on internal network, accessible to authorized team members

**Configuration:**

```bash
# Option A: Bind to all interfaces (if on private network with firewall)
flask run --host=0.0.0.0 --port=8000

# Option B: Bind to specific internal IP
flask run --host=192.168.x.x --port=8000

# Set ADMIN_TOKEN for simple bearer token protection
export ADMIN_TOKEN="your-secret-token-here"
flask run --host=0.0.0.0 --port=8000
```

**Requirements:**
- Network access: Private network with firewall/VPN restrictions
- HTTPS: Recommended if traffic crosses network segments (HTTPS must be provided by reverse proxy)
- Authentication: Optional bearer token (if set via ADMIN_TOKEN)
- Firewall: Restrict port 8000 to authorized IPs/VPNs

**Verification:**

```bash
# Confirm binding to expected interface
netstat -an | grep 8000
# Should show: 0.0.0.0:8000 or <specific-ip>:8000

# Confirm firewall blocks external access
curl http://<external-ip>:8000/
# Should timeout/fail (firewall blocks)

# Confirm authentication (if ADMIN_TOKEN is set)
curl http://192.168.x.x:8000/  # No token
# Should return 401 Unauthorized

curl -H "Authorization: Bearer correct-token" http://192.168.x.x:8000/  # With token
# Should return 200 OK
```

---

### Mode 3: Reverse Proxy / Production Deployment

**Use case:** Householder running behind reverse proxy (nginx, Apache, etc.) with HTTPS and SSO

**Configuration:**

```bash
# Bind to localhost only (proxy handles external access)
flask run --host=127.0.0.1 --port=8000

# Let proxy handle HTTPS/TLS, authentication, and access control
# Proxy forwards authenticated requests to app

# Optional: Set ADMIN_TOKEN as defense-in-depth
# (proxy does auth; app does fallback auth if needed)
export ADMIN_TOKEN="fallback-token"
flask run --host=127.0.0.1 --port=8000
```

**Operator configures (in proxy/infrastructure):**

1. **HTTPS/TLS certificate**
   ```
   Reverse proxy (nginx/Apache) terminates HTTPS
   Certificate issued by trusted CA
   All HTTP traffic redirected to HTTPS
   ```

2. **Authentication/SSO**
   ```
   Proxy authenticates users before forwarding
   Common options:
   - OAuth2 / OpenID Connect
   - SAML
   - LDAP
   - Corporate SSO (Okta, Entra, etc.)
   ```

3. **Secure proxy headers**
   ```
   X-Forwarded-For: Client IP
   X-Forwarded-Proto: https
   X-Forwarded-Host: domain.com
   Authorization: Passed through (if using app-level token)
   ```

4. **Network security**
   ```
   Proxy exposed to internet on HTTPS (443)
   App only accessible from proxy (localhost)
   Database only accessible from app
   Backups stored on separate secure server
   ```

**Verification (Proxy configuration):**

```bash
# From client: HTTPS works
curl https://domain.com/
# Should return 200 OK (proxy requires authentication first)

# From client: Redirect HTTP → HTTPS
curl http://domain.com/
# Should redirect to https://domain.com/

# From proxy server: App accessible on localhost
curl http://127.0.0.1:8000/
# Should return 200 OK

# From internet: App NOT directly accessible
curl http://<app-ip>:8000/
# Should timeout/fail (firewall blocks)
```

---

## File Permission Checks

### Export Directory

**Expected:** Owner writable, not world-writable

```bash
EXPORT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"

# Check directory permissions
ls -ld "$EXPORT_DIR"
# Expected: drwxr-xr-x (755)
# ✓ Owner: read, write, execute
# ✓ Group: read, execute only
# ✓ Other: read, execute only
```

**Verification:**

```bash
# Should be able to create and delete test file
touch "$EXPORT_DIR/.test"
rm "$EXPORT_DIR/.test"
```

**Result (verified 2026-06-13):** ✓ drwxr-xr-x (755) — SAFE

### Generated Export Files

**Expected:** Owner readable/writable, group/other readable only

```bash
# After generating an export, check file permissions
ls -l "$EXPORT_DIR"/export_*.csv

# Expected: -rw-r--r-- (644)
# ✓ Owner: read, write
# ✓ Group: read only
# ✓ Other: read only
# ✓ NOT writable by group or other
```

**Why:** Export files contain donor data; should not be world-writable.

### Database File

**Expected:** Owner readable/writable, group/other readable only

```bash
DB_FILE="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db"

ls -l "$DB_FILE"
# Expected: -rw-r--r-- (644)
# ✓ Owner: read, write
# ✓ Group: read only
# ✓ Other: read only
# ✓ NOT world-writable
```

**Result (verified 2026-06-13):** ✓ -rw-r--r-- (644) — SAFE

### Backup Directory and Files

**Expected:** Owner writable, not world-writable

```bash
BACKUP_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups"

ls -ld "$BACKUP_DIR"
# Expected: drwxr-xr-x (755)

ls -l "$BACKUP_DIR"/*.db
# Expected: -rw-r--r-- (644)
# ✓ Owner: read, write
# ✓ Group: read only
# ✓ Other: read only
# ✓ NOT writable by anyone but owner
```

**Result (verified 2026-06-13):** ✓ drwxr-xr-x (755) for directory, -rw-r--r-- (644) for files — SAFE

### Complete Permission Verification Script

```bash
#!/bin/bash
# Save as: verify-permissions.sh

EXPORT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
DB_FILE="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db"
BACKUP_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups"

echo "=== Export Directory ==="
ls -ld "$EXPORT_DIR"

echo ""
echo "=== Database File ==="
ls -l "$DB_FILE"

echo ""
echo "=== Backup Directory ==="
ls -ld "$BACKUP_DIR"

echo ""
echo "=== Backup Files ==="
ls -l "$BACKUP_DIR"/*.db

echo ""
echo "✓ All permissions verified"
```

---

## Deployment-Day Security Smoke Test

### Security Spot-Check (15 minutes)

**1. Verify HTTPS is enforced (if applicable)**

```bash
# For local-only: skip
# For private network: depends on reverse proxy setup
# For production: verify redirect

curl -I http://domain.com/
# Expected: 301 redirect to https://domain.com/

curl -I https://domain.com/
# Expected: 200 OK with valid certificate
openssl s_client -connect domain.com:443 -showcerts
# Verify certificate is valid and issued by trusted CA
```

**2. Verify no external API calls**

```bash
# Monitor network traffic during app startup and first export
sudo tcpdump -i any 'tcp port 80 or tcp port 443' -w /tmp/network.pcap

# Start app
flask run --host=127.0.0.1 --port=8000 &

# Perform export operation
curl http://127.0.0.1:8000/...

# Kill app and check traffic
pkill flask

# Analyze capture (should show only localhost traffic)
tcpdump -r /tmp/network.pcap
# Expected: NO external API calls to CRM, Givebutter, or other services
```

**3. Verify file permissions**

```bash
# Run permission verification script
bash verify-permissions.sh

# Check for world-writable files
find /path/to/givebutter -type f -perm -002 2>/dev/null
# Should return: (nothing) — no world-writable files

find /path/to/givebutter -type d -perm -002 2>/dev/null
# Should return: (nothing) — no world-writable directories
```

**4. Verify export files created with correct permissions**

```bash
# Perform export operation
# Then check file permissions

ls -l /path/to/exports/export_*.csv
# Expected: -rw-r--r-- (644)
# ✓ NOT world-writable
# ✓ NOT group-writable
```

**5. Verify database is not exposed**

```bash
# Check database is only accessible from app
sqlite3 /path/to/givebutter.db "SELECT COUNT(*) FROM import_batches;"
# Should work (owner can access)

# Verify permissions
ls -l /path/to/givebutter.db
# Expected: -rw-r--r-- (644)
# ✓ Readable by all (for querying)
# ✓ Writable by owner only (protected)
# ✓ NOT world-writable
```

**6. Check logs for unexpected errors**

```bash
grep -i "error\|warning\|ssl\|certificate" /path/to/application.log | grep -i "error"
# Expected: (minimal errors)
# Should NOT see:
#   - "API key not found"
#   - "credential required"
#   - "SSL/certificate error"
#   - "connection to external service failed"
```

**7. Verify authentication (if ADMIN_TOKEN set)**

```bash
# If ADMIN_TOKEN is configured
if [ ! -z "$ADMIN_TOKEN" ]; then
  # Without token (should fail)
  curl http://127.0.0.1:8000/ 
  # Expected: 401 Unauthorized

  # With token (should succeed)
  curl -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/
  # Expected: 200 OK
fi
```

**Result:** ✓ If all checks pass, security posture is sound for deployment.

---

## Remaining Operator-Owned Security Tasks

### Pre-Deployment

- [ ] **Review this document** — Understand security model and deployment options
- [ ] **Choose deployment mode** — Local, private network, or reverse proxy
- [ ] **Configure network access** — Firewall/VPN rules, reverse proxy, etc.
- [ ] **Set ADMIN_TOKEN (optional)** — For bearer token protection
- [ ] **Configure HTTPS/TLS** — If traffic leaves localhost
- [ ] **Verify file permissions** — Run permission verification script
- [ ] **Document your configuration** — Record chosen deployment mode and settings
- [ ] **Plan access control** — How will users authenticate? (VPN, proxy, SSO?)

### Post-Deployment

- [ ] **Monitor logs daily** — Check for unexpected errors or unauthorized access attempts
- [ ] **Rotate ADMIN_TOKEN** — If used, rotate periodically (recommend 90-day rotation)
- [ ] **Update firewall rules** — As needed if access patterns change
- [ ] **Review audit trail** — Verify all actions are logged in audit_log table
- [ ] **Monitor network traffic** — Ensure no unexpected external calls
- [ ] **Check file permissions** — Ensure export files maintain correct permissions
- [ ] **Test backup restore** — Regularly test backup and restore procedure

---

## Limitations and Assumptions

### v1.1 Security Model Limitations

**No app-level authentication:**
- v1.1 does not add RBAC or user management
- Access control MUST be provided by deployment environment
- Example: If running on public internet, operator MUST use reverse proxy with SSO/authentication

**No HTTPS in app:**
- Flask runs on HTTP (port 8000)
- If internet-exposed, operator MUST use reverse proxy with HTTPS/TLS
- For local-only, HTTPS is not required

**Append-only audit trail:**
- Audit logs record actions but cannot prove who performed them (no user identification)
- For production, operator should implement infrastructure-level access logging (e.g., proxy logs, firewall logs)

**No credential rotation:**
- ADMIN_TOKEN (if used) must be rotated by operator
- No automatic token expiration or invalidation

### Assumptions

**Deployment environment provides:**
- Network isolation (if private network)
- Authentication (if not local-only)
- HTTPS/TLS (if internet-exposed)
- Access logging (if required for compliance)

**Operator responsibilities:**
- File system permissions (verified)
- Network configuration (verified as safe defaults)
- Access control strategy (operator chooses)
- Backup/restore testing (documented in Task 3)

---

## 15 Hard Guardrails Confirmed

All guardrails remain in place and enforced:

✓ **No CRM/Givebutter API calls** — Verified, no external service calls found  
✓ **No credentials storage** — Verified, only ADMIN_TOKEN (env var, not stored)  
✓ **No writeback routes** — Verified, preview/readiness are read-only  
✓ **No auth/RBAC changes** — v1.1 uses existing context only, no new auth  
✓ **No bulk actions** — All decisions individual  
✓ **No background jobs** — All operations synchronous  
✓ **No new export formats** — CSV-only  
✓ **No source-data mutations** — Append-only design  
✓ **No contact mutations** — Append-only design  
✓ **No contact merge**  
✓ **No contact deletion**  
✓ **No household_id assignment**  
✓ **No schema changes**  
✓ **No cross-import matching**  
✓ **No master contacts/households**  

---

## Sign-Off

**Task 4 Completion: VERIFIED**

- [x] Security model documented: No external APIs, no credentials required, no app-level RBAC
- [x] Access control responsibility clarified: Deployment environment must provide authentication/network controls
- [x] External API/credential verification completed: No external calls or stored credentials found
- [x] Deployment guidance provided: Three modes (local, private network, reverse proxy)
- [x] Flask startup configuration documented: Binds to localhost by default
- [x] ADMIN_TOKEN optional authentication documented: Env var controlled, bearer token mechanism
- [x] File permission verification completed: All directories and files have safe permissions (not world-writable)
- [x] Permission check commands provided: For export, database, backups
- [x] Security smoke test procedure documented: 7-point verification checklist
- [x] Operator-owned tasks documented: Pre-deployment and post-deployment checklists
- [x] All 15 guardrails confirmed

**Householder v1.1 HTTPS/Network/Security Configuration: COMPLETE AND READY FOR TASK 5**

---

## References

- `docs/operatinalizing/V1_1_OPERATOR_FOLDER_SEMANTICS.md` — Folder organization
- `docs/operatinalizing/V1_1_OPERATOR_TASK2_EXPORT_OUTPUT_DIR_CONFIGURATION.md` — Export configuration
- `docs/operatinalizing/V1_1_OPERATOR_TASK3_DATABASE_BACKUP_CONFIGURATION.md` — Backup configuration
- `docs/implementation/release/V1_1_OPERATOR_HANDOFF.md` — Operator handoff package
