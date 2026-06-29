"""
etsy_oauth.py — one-time OAuth2 setup to get your Etsy refresh token.

Run this ONCE locally, then add the printed token as GitHub secret ETSY_REFRESH_TOKEN.

Usage:
  ETSY_API_KEY=your_key ETSY_REDIRECT_URI=http://localhost:12345 python etsy_oauth.py

Steps:
  1. Go to etsy.com/developers → create an app
  2. Set redirect URI to http://localhost:12345 in the app settings
  3. Run this script with your ETSY_API_KEY
  4. Paste the redirect URL when prompted
  5. Copy the printed refresh_token → add as GitHub secret ETSY_REFRESH_TOKEN
"""

import os
import re
import hashlib
import base64
import secrets
import urllib.parse
import requests

API_KEY      = os.environ["ETSY_API_KEY"]
REDIRECT_URI = os.environ.get("ETSY_REDIRECT_URI", "http://localhost:12345")
SCOPES       = "listings_r listings_w listings_d shops_r shops_w"

# PKCE
verifier  = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()

state = secrets.token_hex(8)

auth_url = (
    "https://www.etsy.com/oauth/connect?"
    + urllib.parse.urlencode({
        "response_type":         "code",
        "redirect_uri":          REDIRECT_URI,
        "scope":                 SCOPES,
        "client_id":             API_KEY,
        "state":                 state,
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
    })
)

print("\n1. Open this URL in your browser:\n")
print(auth_url)
print("\n2. Approve access, then paste the FULL redirect URL here:")
redirect_response = input("> ").strip()

code_match = re.search(r"[?&]code=([^&]+)", redirect_response)
if not code_match:
    raise SystemExit("No 'code' found in redirect URL")

code = code_match.group(1)

r = requests.post(
    "https://api.etsy.com/v3/public/oauth/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "grant_type":            "authorization_code",
        "client_id":             API_KEY,
        "redirect_uri":          REDIRECT_URI,
        "code":                  code,
        "code_verifier":         verifier,
    },
)
r.raise_for_status()
data = r.json()

print("\n✓ Success! Add these as GitHub secrets:\n")
print(f"ETSY_ACCESS_TOKEN  = {data['access_token']}")
print(f"ETSY_REFRESH_TOKEN = {data['refresh_token']}")
