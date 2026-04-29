import requests

import os
from dotenv import load_dotenv

load_dotenv('replate/.env')
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = "1475686827393876"
API_VERSION = "v21.0"

def debug_meta():
    print(f"--- Debugging Meta Access ---")
    # Test 1: Check self
    me_url = f"https://graph.facebook.com/{API_VERSION}/me?access_token={ACCESS_TOKEN}"
    print(f"GET /me: {requests.get(me_url).json()}")

    # Test 2: Check Ad Account existence
    acc_url = f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}?fields=name,account_status&access_token={ACCESS_TOKEN}"
    print(f"GET /act_{AD_ACCOUNT_ID}: {requests.get(acc_url).json()}")

if __name__ == "__main__":
    debug_meta()
