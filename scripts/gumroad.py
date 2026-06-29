"""
gumroad.py — auto-create and publish products on Gumroad via API v2.
Each product gets a unique BTC payment note in the description.
"""

import os
import requests

BASE_URL = "https://api.gumroad.com/v2"
TOKEN    = os.environ.get("GUMROAD_TOKEN", "")


def create_product(
    title:       str,
    description: str,
    pdf_path:    str,
    price_usd:   float = 4.99,
    btc_address: str   = "",
) -> dict:
    """
    Creates a new Gumroad product, uploads the PDF, publishes it.
    Returns the Gumroad product dict on success.
    """
    if not TOKEN:
        raise RuntimeError("GUMROAD_TOKEN env var not set")

    # ── Step 1: Create the product ────────────────────────────────────────────
    full_description = description
    if btc_address:
        full_description += (
            f"\n\n---\n"
            f"**Pay with Bitcoin:** Send exact amount to:\n"
            f"`{btc_address}`\n"
            f"Then email your transaction ID to receive the download link."
        )

    r = requests.post(f"{BASE_URL}/products", data={
        "access_token":  TOKEN,
        "name":          title,
        "description":   full_description,
        "price":         int(price_usd * 100),  # cents
        "published":     True,
        "url":           "",
    })
    r.raise_for_status()
    product = r.json()["product"]
    product_id = product["id"]

    # ── Step 2: Upload the PDF as the product file ────────────────────────────
    with open(pdf_path, "rb") as f:
        ru = requests.put(
            f"{BASE_URL}/products/{product_id}/files",
            data={"access_token": TOKEN},
            files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
        )
        ru.raise_for_status()

    print(f"[gumroad] Listed: {title} → {product.get('short_url', product_id)}")
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


if __name__ == "__main__":
    products = fetch_all_products()
    print(f"Products on Gumroad: {len(products)}")
