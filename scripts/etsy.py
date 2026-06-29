"""
etsy.py — auto-list PDF guides on Etsy as digital downloads.
Etsy API v3: https://developers.etsy.com/documentation/

Required env vars:
  ETSY_API_KEY       — keystring from your Etsy app (etsy.com/developers)
  ETSY_SHOP_ID       — your Etsy shop numeric ID (or shop name)
  ETSY_REFRESH_TOKEN — OAuth2 refresh token (run etsy_oauth.py once to get this)

One-time setup: python scripts/etsy_oauth.py
"""

import os
import requests

BASE_URL = "https://openapi.etsy.com/v3"
API_KEY  = os.environ.get("ETSY_API_KEY", "")
SHOP_ID  = os.environ.get("ETSY_SHOP_ID", "")

# Digital guides/printables taxonomy on Etsy
TAXONOMY_ID = 2078   # Craft Supplies > Patterns & How To

_cached_token: str = ""


def _get_token() -> str:
    """Exchange refresh token for a fresh access token (valid 1h)."""
    global _cached_token
    if _cached_token:
        return _cached_token

    refresh = os.environ.get("ETSY_REFRESH_TOKEN", "")
    direct  = os.environ.get("ETSY_ACCESS_TOKEN", "")

    if not refresh:
        if not direct:
            raise RuntimeError("ETSY_REFRESH_TOKEN or ETSY_ACCESS_TOKEN not set")
        return direct

    r = requests.post(
        "https://api.etsy.com/v3/public/oauth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":    "refresh_token",
            "client_id":     API_KEY,
            "refresh_token": refresh,
        },
    )
    r.raise_for_status()
    _cached_token = r.json()["access_token"]
    return _cached_token


def _headers() -> dict:
    return {
        "x-api-key":     API_KEY,
        "Authorization": f"Bearer {_get_token()}",
    }


def create_listing(title: str, description: str, price_usd: float, tags: list[str]) -> dict:
    """Create a digital download listing. Returns listing dict."""
    if not API_KEY or not SHOP_ID:
        raise RuntimeError("ETSY_API_KEY or ETSY_SHOP_ID not set")

    r = requests.post(
        f"{BASE_URL}/application/shops/{SHOP_ID}/listings",
        headers={**_headers(), "Content-Type": "application/json"},
        json={
            "title":         title[:140],
            "description":   description[:65000],
            "price":         round(price_usd, 2),
            "quantity":      999,
            "who_made":      "i_did",
            "when_made":     "made_to_order",
            "taxonomy_id":   TAXONOMY_ID,
            "tags":          [t[:20] for t in tags[:13]],
            "type":          "download",
            "shipping_profile_id": None,   # not required for digital
        },
    )
    r.raise_for_status()
    listing = r.json()
    listing_id = listing.get("listing_id") or listing.get("id")
    print(f"[etsy] Created listing {listing_id}: {title[:60]}")
    return listing


def upload_file(listing_id: int, pdf_path: str) -> dict:
    """Attach the PDF as the digital download for the listing."""
    with open(pdf_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/application/shops/{SHOP_ID}/listings/{listing_id}/files",
            headers=_headers(),
            files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
            data={"name": os.path.basename(pdf_path), "rank": 1},
        )
    r.raise_for_status()
    return r.json()


def publish_listing(listing_id: int) -> dict:
    """Move listing from draft → active."""
    r = requests.patch(
        f"{BASE_URL}/application/shops/{SHOP_ID}/listings/{listing_id}",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"state": "active"},
    )
    r.raise_for_status()
    result = r.json()
    listing_url = f"https://www.etsy.com/listing/{listing_id}"
    print(f"[etsy] Published: {listing_url}")
    return result


def list_product(title: str, description: str, price_usd: float,
                 tags: list[str], pdf_path: str) -> str:
    """Full flow: create → upload file → publish. Returns Etsy listing URL."""
    listing    = create_listing(title, description, price_usd, tags)
    listing_id = listing.get("listing_id") or listing.get("id")
    upload_file(listing_id, pdf_path)
    publish_listing(listing_id)
    return f"https://www.etsy.com/listing/{listing_id}"
