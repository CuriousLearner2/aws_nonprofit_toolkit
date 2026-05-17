import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path so we can import our package
sys.path.append(str(Path.cwd()))

from aws_nonprofit_toolkit.meta_growth_engine import MetaConfig, create_custom_audience

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("sandbox_test")

def test_sandbox():
    load_dotenv()
    
    token = os.getenv("META_ACCESS_TOKEN")
    sandbox_id = os.getenv("META_SANDBOX_AD_ACCOUNT_ID")
    
    print("\n" + "="*50)
    print("META SANDBOX INTEGRATION TEST")
    print("="*50)
    
    if not token or not sandbox_id:
        print("❌ FAILED: Missing META_ACCESS_TOKEN or META_SANDBOX_AD_ACCOUNT_ID in .env")
        print("Please update your .env file before running this test.")
        return

    _, config_sandbox_id = MetaConfig.get_credentials(use_sandbox=True)
    print(f"Token Found:      {token[:5]}...{token[-5:]}")
    print(f"Sandbox Account:  act_{sandbox_id}")
    print(f"MetaConfig ID:    act_{config_sandbox_id}")
    print("-" * 50)

    try:
        # Step 1: Validate Configuration
        MetaConfig.validate(use_sandbox=True)
        print("✅ Step 1: Configuration is valid.")

        # Step 2: Try a Dry-Run Creation using the actual package logic
        print("⏳ Step 2: Running dry-run audience creation...")
        aud_id = create_custom_audience(
            "Sandbox Connection Test", 
            ad_account_id=sandbox_id, 
            dry_run=True
        )
        
        if aud_id == "dry_run_audience_id":
            print("✅ Step 2: Dry-run logic successful.")

        print("-" * 50)
        print("🚀 NEXT STEP: Run a LIVE sandbox sync with:")
        print(f"python3 aws_nonprofit_toolkit/meta_growth_engine.py --sandbox --create-lookalike")
        print("="*50 + "\n")

    except ValueError as e:
        print(f"❌ CONFIG ERROR: {e}")
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    test_sandbox()
