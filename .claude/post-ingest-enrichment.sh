#!/bin/bash
# Auto-enrichment hook: runs full enrichment pipeline after email ingest

# Read the hook input from stdin
input=$(cat)

# Extract the command that was just executed
command=$(echo "$input" | jq -r '.tool_input.command // empty')

# Only proceed if this was an ingest command (gmail_ingest, ingest.py, or run_ingest.sh)
if ! echo "$command" | grep -qE "(gmail_ingest|ingest\.py|run_ingest)"; then
    exit 0
fi
    echo "Post-ingest enrichment triggered..."

    # Change to project directory
    if ! cd "/Users/gautambiswas/Claude Code"; then
        echo "ERROR: Failed to cd to project directory"
        exit 1
    fi

    # Run full enrichment pipeline with error handling
    python3 << 'EOPYTHON' || true
import sqlite3
import sys
import os
from datetime import datetime

# Verify required modules exist before proceeding
required_modules = [
    ("listings.earthquake_hazard", "assess_earthquake_risk"),
    ("listings.fire_hazard", "get_fire_hazard_zone"),
    ("listings.bpn_enrichment", "run_bpn_enrichment"),
    ("listings.geocoder", "run_geocoder"),
]

missing_modules = []
for module_name, func_name in required_modules:
    try:
        mod = __import__(module_name, fromlist=[func_name])
        if not hasattr(mod, func_name):
            missing_modules.append(f"{module_name}.{func_name}")
    except ImportError:
        missing_modules.append(module_name)

if missing_modules:
    print(f"WARNING: Missing modules: {', '.join(missing_modules)}")
    print("Enrichment will continue with available modules")
    sys.exit(0)

# Safe imports with fallback
try:
    from listings.earthquake_hazard import assess_earthquake_risk
except ImportError:
    assess_earthquake_risk = None

try:
    from listings.fire_hazard import get_fire_hazard_zone
except ImportError:
    get_fire_hazard_zone = None

try:
    from listings.bpn_enrichment import run_bpn_enrichment
except ImportError:
    run_bpn_enrichment = None

try:
    from listings.geocoder import run_geocoder
except ImportError:
    run_geocoder = None

db_path = "listings/listings.db"
if not os.path.exists(db_path):
    print(f"ERROR: Database not found at {db_path}")
    sys.exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
except Exception as e:
    print(f"ERROR: Failed to connect to database: {e}")
    sys.exit(1)

# Get the last successful enrichment timestamp
cursor.execute("SELECT value FROM sync_state WHERE key = 'last_enrichment_completed'")
result = cursor.fetchone()
last_enrichment = result[0] if result else "2020-01-01T00:00:00"  # Default to old date if never enriched
enrichment_start_time = datetime.utcnow().isoformat()

print(f"Last successful enrichment: {last_enrichment}")
print(f"Enriching listings since: {last_enrichment}\n")

# Step 1: Assign neighborhoods to listings without them (only new listings)
import time
step1_start = time.time()
print("Step 1: Assigning neighborhoods to listings...")
cursor.execute("""
    SELECT COUNT(*) FROM listings WHERE neighborhood IS NULL AND address IS NOT NULL AND received_at > ?
""", (last_enrichment,))
unassigned = cursor.fetchone()[0]
if unassigned > 0:
    # Listings without neighborhoods - try to extract from city or use generic assignment
    cursor.execute("""
        SELECT id, city, state FROM listings WHERE neighborhood IS NULL AND address IS NOT NULL AND received_at > ?
    """, (last_enrichment,))
    for listing_id, city, state in cursor.fetchall():
        # Use city as neighborhood if available
        neighborhood = city if city else None
        if neighborhood:
            cursor.execute("UPDATE listings SET neighborhood = ? WHERE id = ?", (neighborhood, listing_id))
    conn.commit()
    print(f"  Assigned neighborhoods to {unassigned} listings")
step1_elapsed = time.time() - step1_start
print(f"  ⏱ Step 1 took {step1_elapsed:.1f}s\n")

# Step 2: Geocode addresses and add coordinates
step2_start = time.time()
print("Step 2: Geocoding addresses...")
try:
    if run_geocoder:
        geocoded = run_geocoder(conn)
        print(f"  Geocoded {geocoded} listings")
    else:
        print("  ⚠ Geocoder module not available, skipping")
        geocoded = 0
except Exception as e:
    print(f"  ⚠ Geocoding failed: {e}")
    geocoded = 0
step2_elapsed = time.time() - step2_start
print(f"  ⏱ Step 2 took {step2_elapsed:.1f}s\n")

# Step 3: Seismic and fire hazard enrichment (only new listings)
step3_start = time.time()
print("Step 3: Enriching with seismic and fire hazard data...")
cursor.execute("""
    SELECT id, address, latitude, longitude
    FROM listings
    WHERE latitude IS NOT NULL
    AND longitude IS NOT NULL
    AND (seismic_zone IS NULL OR fire_zone IS NULL)
    AND received_at > ?
    ORDER BY received_at DESC
""", (last_enrichment,))

properties = cursor.fetchall()

if properties:
    print(f"  Enriching {len(properties)} listings with risk data...")

    seismic_time = 0
    fire_time = 0
    skipped_count = 0

    for i, (prop_id, address, lat, lon) in enumerate(properties):
        try:
            if (i + 1) % 25 == 0:
                print(f"    [{i + 1}/{len(properties)}] processed...")

            seismic = None
            fire = None

            # Get seismic data if available
            if assess_earthquake_risk:
                try:
                    seismic_t0 = time.time()
                    seismic = assess_earthquake_risk(lat, lon)
                    seismic_time += time.time() - seismic_t0
                except Exception as e:
                    pass  # Skip seismic if it fails

            # Get fire data if available
            if get_fire_hazard_zone:
                try:
                    fire_t0 = time.time()
                    fire = get_fire_hazard_zone(lat, lon)
                    fire_time += time.time() - fire_t0
                except Exception as e:
                    pass  # Skip fire if it fails

            # Only update if we have at least some data
            if seismic or fire:
                fire_zone = fire.get('zone_name') if fire else None
                fire_score = fire.get('risk_score') if fire else None
                conn.execute("""
                    UPDATE listings
                    SET seismic_zone = ?, seismic_risk_score = ?, fire_zone = ?, fire_risk_score = ?
                    WHERE id = ?
                """, (seismic['seismic_zone'] if seismic else None, seismic['risk_score'] if seismic else None, fire_zone, fire_score, prop_id))
            else:
                skipped_count += 1

        except Exception as e:
            skipped_count += 1
            pass  # Skip on error, continue with next property

    conn.commit()
    print(f"    Seismic: {seismic_time:.1f}s | Fire: {fire_time:.1f}s")
    print("  ✓ Risk enrichment complete")
else:
    print("  No listings need risk enrichment")

step3_elapsed = time.time() - step3_start
print(f"  ⏱ Step 3 took {step3_elapsed:.1f}s\n")

# Step 4: BPN sentiment enrichment (only for NEW listings to keep it fast)
step4_start = time.time()
print("Step 4: Enriching with BPN sentiment (new neighborhoods only)...")
try:
    if run_bpn_enrichment:
        # Only analyze neighborhoods from new listings (received_at > last_enrichment)
        run_bpn_enrichment(conn, since_timestamp=last_enrichment)
        print("  ✓ BPN enrichment complete")
    else:
        print("  ⚠ BPN enrichment module not available, skipping")
except Exception as e:
    print(f"  ⚠ BPN enrichment skipped: {e}")
step4_elapsed = time.time() - step4_start
print(f"  ⏱ Step 4 took {step4_elapsed:.1f}s\n")

# Summary timing
total_elapsed = step1_elapsed + step2_elapsed + step3_elapsed + step4_elapsed
print(f"═══════════════════════════════════════")
print(f"ENRICHMENT TIMING SUMMARY:")
print(f"  Step 1 (Neighborhoods): {step1_elapsed:.1f}s")
print(f"  Step 2 (Geocoding):     {step2_elapsed:.1f}s")
print(f"  Step 3 (Risk):          {step3_elapsed:.1f}s")
print(f"  Step 4 (BPN):           {step4_elapsed:.1f}s")
print(f"  ──────────────────────────")
print(f"  TOTAL:                  {total_elapsed:.1f}s")
print(f"═══════════════════════════════════════\n")

conn.close()

# Verify enrichment completion
print("\nVerifying enrichment completion...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check geocoding
cursor.execute("SELECT COUNT(*) FROM listings WHERE geocoded_at IS NULL AND address IS NOT NULL")
ungeocoded = cursor.fetchone()[0]

# Check seismic/fire enrichment
cursor.execute("SELECT COUNT(*) FROM listings WHERE latitude IS NOT NULL AND seismic_zone IS NULL")
unseismic = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM listings WHERE latitude IS NOT NULL AND fire_zone IS NULL")
unfire = cursor.fetchone()[0]

# Check BPN sentiment coverage
cursor.execute("SELECT COUNT(DISTINCT neighborhood) FROM listings WHERE neighborhood IS NOT NULL")
neighborhoods = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM neighborhood_sentiment")
sentiment_records = cursor.fetchone()[0]

conn.close()

# Report verification results and log failures
import os

log_file = os.path.expanduser("~/.claude/enrichment.log")

def log_message(msg):
    """Log to file and stdout."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {msg}"
    print(log_entry)
    try:
        with open(log_file, "a") as f:
            f.write(log_entry + "\n")
    except:
        pass

all_good = True
failures = []

if ungeocoded > 0:
    msg = f"⚠ Geocoding incomplete: {ungeocoded} listings without coordinates"
    print(f"  {msg}")
    failures.append("geocoding")
    all_good = False
else:
    print("  ✓ Geocoding complete (100%)")

if unseismic > 0:
    msg = f"⚠ Seismic enrichment incomplete: {unseismic} listings missing data"
    print(f"  {msg}")
    failures.append("seismic")
    all_good = False
else:
    print("  ✓ Seismic enrichment complete (100%)")

if unfire > 0:
    msg = f"⚠ Fire hazard enrichment incomplete: {unfire} listings missing data"
    print(f"  {msg}")
    failures.append("fire")
    all_good = False
else:
    print("  ✓ Fire hazard enrichment complete (100%)")

if neighborhoods > 0 and sentiment_records < neighborhoods:
    missing = neighborhoods - sentiment_records
    msg = f"⚠ BPN sentiment incomplete: {missing}/{neighborhoods} neighborhoods missing (check if neighborhoods are BPN pages)"
    print(f"  {msg}")
    failures.append("bpn_sentiment")
    all_good = False
elif neighborhoods > 0:
    print(f"  ✓ BPN sentiment complete ({sentiment_records}/{neighborhoods} neighborhoods)")
else:
    print("  ℹ No neighborhoods to analyze")

if all_good:
    log_message(f"✓ Enrichment complete: {ungeocoded + unseismic + unfire} issues")
    print("✓ Full enrichment pipeline complete - all data verified")

    # Store the enrichment completion timestamp for next run
    import sqlite3
    conn_final = sqlite3.connect(db_path)
    conn_final.execute(
        "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
        ("last_enrichment_completed", enrichment_start_time)
    )
    conn_final.commit()
    conn_final.close()
    print(f"✓ Saved enrichment timestamp: {enrichment_start_time}")
else:
    reason = ", ".join(failures) if failures else "unknown"
    log_message(f"✗ Enrichment incomplete: {reason}")
    print(f"⚠ Enrichment verification found gaps: {reason}")
    print(f"ℹ Enrichment timestamp NOT updated - will retry next run")
EOPYTHON
