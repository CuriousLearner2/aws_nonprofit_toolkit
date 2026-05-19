#!/usr/bin/env python3
"""
Verification script for the Donor Sync Pipeline.
Reports on sandbox audience status, match rates, and readiness for ad targeting.
"""

import os
import sys
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

class PipelineVerifier:
    """Verify donor sync pipeline status in Meta sandbox."""

    def __init__(self):
        self.api_version = "v21.0"
        self.token = os.getenv("META_ACCESS_TOKEN")
        self.sandbox_id = os.getenv("META_SANDBOX_AD_ACCOUNT_ID")
        self.ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.errors = []
        self.warnings = []

    def validate_credentials(self) -> bool:
        """Check if all required credentials are set."""
        print("\n" + "="*60)
        print("STEP 1: CHECKING CREDENTIALS")
        print("="*60)

        checks = [
            ("META_ACCESS_TOKEN", self.token),
            ("META_SANDBOX_AD_ACCOUNT_ID", self.sandbox_id),
            ("META_AD_ACCOUNT_ID", self.ad_account_id),
        ]

        all_valid = True
        for var_name, value in checks:
            if value:
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"✅ {var_name}: {masked}")
            else:
                print(f"❌ {var_name}: NOT SET")
                self.errors.append(f"{var_name} is missing")
                all_valid = False

        if not all_valid:
            print("\n⚠️  Missing credentials. Update your .env file and retry.")
            return False

        return True

    def test_token_validity(self) -> bool:
        """Test if the access token is valid."""
        print("\n" + "="*60)
        print("STEP 2: TESTING TOKEN VALIDITY")
        print("="*60)

        try:
            url = f"{self.base_url}/debug_token"
            params = {"input_token": self.token, "access_token": self.token}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json().get("data", {})
            is_valid = data.get("is_valid", False)

            if is_valid:
                app_id = data.get("app_id", "unknown")
                print(f"✅ Token is valid (App ID: {app_id})")
                return True
            else:
                print(f"❌ Token is invalid or expired")
                self.errors.append("Access token is invalid")
                return False
        except Exception as e:
            print(f"❌ Token validation failed: {str(e)}")
            self.errors.append(f"Token validation error: {str(e)}")
            return False

    def get_account_info(self) -> bool:
        """Get sandbox account info."""
        print("\n" + "="*60)
        print("STEP 3: CHECKING SANDBOX ACCOUNT")
        print("="*60)

        try:
            url = f"{self.base_url}/act_{self.sandbox_id}"
            params = {
                "fields": "name,account_status,is_sandbox",
                "access_token": self.token
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            name = data.get("name", "Unknown")
            status = data.get("account_status", "unknown")
            is_sandbox = data.get("is_sandbox", False)

            print(f"Account Name: {name}")
            print(f"Account Status: {status}")
            print(f"Is Sandbox: {is_sandbox}")

            if status == 1:
                print("✅ Sandbox account is ACTIVE")
                return True
            else:
                print(f"❌ Sandbox account status is not active: {status}")
                self.errors.append(f"Account status: {status}")
                return False
        except Exception as e:
            print(f"❌ Failed to get account info: {str(e)}")
            self.errors.append(f"Account info error: {str(e)}")
            return False

    def list_audiences(self) -> dict:
        """List all custom audiences in sandbox."""
        print("\n" + "="*60)
        print("STEP 4: LISTING AUDIENCES")
        print("="*60)

        try:
            url = f"{self.base_url}/act_{self.sandbox_id}/customaudiences"
            params = {
                "fields": "id,name,subtype,approximate_count,status,created_time",
                "access_token": self.token,
                "limit": 100
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            audiences = response.json().get("data", [])

            if not audiences:
                print("No audiences found in sandbox.")
                return {}

            print(f"Found {len(audiences)} audience(s):\n")

            result = {}
            for aud in audiences:
                aud_id = aud.get("id")
                aud_name = aud.get("name")
                aud_type = aud.get("subtype", "CUSTOM")
                aud_count = aud.get("approximate_count", 0)
                aud_status = aud.get("status", "unknown")
                aud_created = aud.get("created_time", "unknown")

                result[aud_id] = {
                    "name": aud_name,
                    "type": aud_type,
                    "count": aud_count,
                    "status": aud_status,
                    "created": aud_created
                }

                status_icon = "✅" if aud_status == "READY" else "⏳" if aud_status == "BUILDING" else "❓"
                type_icon = "🌱" if aud_type == "CUSTOM" else "🎯" if aud_type == "LOOKALIKES" else "?"

                print(f"{status_icon} {type_icon} {aud_name}")
                print(f"   ID: {aud_id}")
                print(f"   Type: {aud_type}")
                print(f"   Status: {aud_status}")
                print(f"   Size: {aud_count:,} users")
                print(f"   Created: {aud_created}\n")

            return result
        except Exception as e:
            print(f"❌ Failed to list audiences: {str(e)}")
            self.errors.append(f"List audiences error: {str(e)}")
            return {}

    def verify_seed_audience(self, audiences: dict) -> bool:
        """Find and verify the seed audience."""
        print("\n" + "="*60)
        print("STEP 5: VERIFYING SEED AUDIENCE")
        print("="*60)

        # Look for seed audiences (CUSTOM type)
        seed_audiences = {
            aud_id: aud for aud_id, aud in audiences.items()
            if aud.get("type") == "CUSTOM"
        }

        if not seed_audiences:
            print("⚠️  No CUSTOM (seed) audiences found.")
            self.warnings.append("No seed audiences in sandbox")
            return False

        print(f"Found {len(seed_audiences)} seed audience(s):")

        for aud_id, aud in seed_audiences.items():
            name = aud.get("name")
            count = aud.get("count", 0)
            status = aud.get("status")

            print(f"\n🌱 {name}")
            print(f"   Status: {status}")
            print(f"   Donors matched: {count:,}")

            if status == "READY" and count > 0:
                print(f"   ✅ Seed is READY and has {count} donors")
            elif status == "BUILDING":
                print(f"   ⏳ Still building... ({count} donors so far)")
            else:
                print(f"   ⚠️  Status is {status}")

        return any(aud.get("status") == "READY" for aud in seed_audiences.values())

    def verify_lookalike_audience(self, audiences: dict) -> bool:
        """Find and verify lookalike audiences."""
        print("\n" + "="*60)
        print("STEP 6: VERIFYING LOOKALIKE AUDIENCE")
        print("="*60)

        # Look for lookalike audiences
        lookalike_audiences = {
            aud_id: aud for aud_id, aud in audiences.items()
            if aud.get("type") == "LOOKALIKES"
        }

        if not lookalike_audiences:
            print("⚠️  No LOOKALIKES audiences found.")
            print("   (Run the pipeline with --create-lookalike to generate one)")
            self.warnings.append("No lookalike audiences created yet")
            return False

        print(f"Found {len(lookalike_audiences)} lookalike(s):")

        all_ready = True
        for aud_id, aud in lookalike_audiences.items():
            name = aud.get("name")
            count = aud.get("count", 0)
            status = aud.get("status")

            print(f"\n🎯 {name}")
            print(f"   Status: {status}")
            print(f"   Lookalike size: {count:,} users")

            if status == "READY" and count > 100000:
                print(f"   ✅ Lookalike is READY with {count:,} users (good size for targeting)")
            elif status == "READY" and count > 10000:
                print(f"   ✅ Lookalike is READY with {count:,} users (acceptable for targeting)")
            elif status == "READY":
                print(f"   ⚠️  Lookalike is READY but small ({count:,} users)")
            elif status == "BUILDING":
                print(f"   ⏳ Still building... ({count:,} users so far)")
            else:
                print(f"   ❌ Status is {status}")
                all_ready = False

        return all_ready

    def print_summary(self) -> None:
        """Print final verification summary."""
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
            print("\nPipeline Status: FAILED")
            return

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")

        if not self.warnings and not self.errors:
            print("\n✅ All checks passed!")
            print("Pipeline Status: READY FOR AD TARGETING")
        else:
            print("\nPipeline Status: PARTIAL (fix warnings to proceed)")

    def run(self) -> bool:
        """Run complete verification."""
        print("\n" + "="*60)
        print("DONOR SYNC PIPELINE VERIFICATION")
        print("="*60)
        print(f"Sandbox Account: act_{self.sandbox_id}")

        # Run checks
        if not self.validate_credentials():
            self.print_summary()
            return False

        if not self.test_token_validity():
            self.print_summary()
            return False

        if not self.get_account_info():
            self.print_summary()
            return False

        audiences = self.list_audiences()
        if not audiences:
            print("⚠️  No audiences to verify yet.")
            self.print_summary()
            return False

        self.verify_seed_audience(audiences)
        self.verify_lookalike_audience(audiences)

        self.print_summary()
        return len(self.errors) == 0


if __name__ == "__main__":
    verifier = PipelineVerifier()
    success = verifier.run()
    sys.exit(0 if success else 1)
