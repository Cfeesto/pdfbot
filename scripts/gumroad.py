"""
gumroad.py — auto-create and publish products on Gumroad via API v2.
Each product gets a unique BTC payment note in the description.
"""

import os
import requests

BASE_URL = "https://api.gumroad.com/v2"
TOKEN    = os.environ.get("GUMROAD_TOKEN", "")


def create_product(
    title:        str,
    description:  str,
    pdf_path:     str,
    price_usd:    float = 4.99,
    btc_address:  str   = "",
    download_url: str   = "",
) -> dict:
    """
    Creates a Gumroad product with the GitHub Release URL as the content link.
    Customers get the download URL automatically after purchase.
    Returns the Gumroad product dict on success.
    """
    if not TOKEN:
        raise RuntimeError("GUMROAD_TOKEN env var not set")

    full_description = description
    if btc_address:
        full_description += (
            f"\n\n---\n"
            f"**Pay with Bitcoin:** Send exact amount to:\n"
            f"`{btc_address}`\n"
            f"Email your transaction ID to get the download link instantly."
        )

    # Use GitHub Release URL as the product content URL
    # Gumroad sends this link to the buyer after payment
    r = requests.post(f"{BASE_URL}/products", data={
        "access_token": TOKEN,
        "name":         title,
        "description":  full_description,
        "price":        int(price_usd * 100),  # cents
        "published":    True,
        "url":          download_url,          # GitHub Release download link
    })
    r.raise_for_status()
    product = r.json()["product"]
    print(f"[gumroad] Listed: {title} → {product.get('short_url', product['id'])}")
    return product


def fetch_sales(product_id: str | None = None) -> list[dict]:
    """Fetch recent sales. If product_id given, filter to that product."""
    r = requests.get(f"{BASE_URL}/sales", params={
        "access_token": TOKEN,
        "product_id":   product_id or "",
    })
    r.raise_for_status()
    return r.json().get("sales", [])


def fetch_all_products() -> list[dict]:
    """Return all published products."""
    r = requests.get(f"{BASE_URL}/products", params={"access_token": TOKEN})
    r.raise_for_status()
    return r.json().get("products", [])


def enable_affiliate(product_id: str, commission_pct: int = 25) -> dict:
    """Enable affiliate programme so others can earn commission promoting the product."""
    r = requests.patch(f"{BASE_URL}/products/{product_id}", data={
        "access_token":                TOKEN,
        "affiliate_offer_description": f"Earn {commission_pct}% commission promoting this guide",
        "affiliate_offer":             True,
    })
    r.raise_for_status()
    product = r.json().get("product", {})
    print(f"[gumroad] Affiliate {commission_pct}% enabled: {product_id}")
    return product


if __name__ == "__main__":
    products = fetch_all_products()
    print(f"Products on Gumroad: {len(products)}")
