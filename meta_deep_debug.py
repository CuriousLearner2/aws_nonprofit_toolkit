import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
# Note: Using the new verified sandbox ID
SANDBOX_ID = os.getenv("META_SANDBOX_AD_ACCOUNT_ID")
AD_ACCOUNT_ID = f"act_{SANDBOX_ID}"
API_VERSION = "v21.0"
# --------------

base = f"https://graph.facebook.com/{API_VERSION}"

def get(path, params=None):
    params = params or {}
    params['access_token'] = ACCESS_TOKEN
    r = requests.get(f"{base}/{path}", params=params)
    return r

def post(path, data):
    data['access_token'] = ACCESS_TOKEN
    r = requests.post(f"{base}/{path}", data=data)
    return r

print("\n" + "="*50)
print("1) Token debug")
tok = get("debug_token", {"input_token": ACCESS_TOKEN})
print(json.dumps(tok.json(), indent=2))

print("\n" + "="*50)
print("2) Ad account info")
acct = get(AD_ACCOUNT_ID, {"fields":"account_status,business,is_sandbox,name"})
print(json.dumps(acct.json(), indent=2))

print("\n" + "="*50)
print("3) Custom Audience TOS status")
tos = get(f"{AD_ACCOUNT_ID}/customaudiencestos")
print(json.dumps(tos.json(), indent=2))

print("\n" + "="*50)
print("4) Attempt minimal audience creation (WEBSITE type)")
payload = {
    "name": "Debug Sandbox Audience",
    "subtype": "WEBSITE",
    "description": "debug test",
    "retention_days": 30,
    "rule": '{"url":{"i_contains":""}}',
    "prefill": "1"
}
resp = post(f"{AD_ACCOUNT_ID}/customaudiences", payload)
print("Status:", resp.status_code)
print(json.dumps(resp.json(), indent=2))
print("="*50 + "\n")
