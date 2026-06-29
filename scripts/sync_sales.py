"""
sync_sales.py — fetch Gumroad sales + BTC transactions, update data/sales.json.
Called by sales-check.yml every 30 minutes.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from gumroad  import fetch_sales
from payments import payment_summary

SALES_FILE    = Path(__file__).parent.parent / "data" / "sales.json"
PRODUCTS_FILE = Path(__file__).parent.parent / "data" / "products.json"


def run():
    # Load existing
    existing = json.loads(SALES_FILE.read_text()) if SALES_FILE.exists() else {
        "gumroad_sales": [],
        "btc_summary":   {},
        "last_updated":  None,
    }

    # Gumroad sales
    try:
        raw_sales = fetch_sales()
        existing["gumroad_sales"] = raw_sales
        print(f"[sync] Gumroad sales: {len(raw_sales)}")
    except Exception as e:
        print(f"[sync] Gumroad fetch failed: {e}")

    # BTC payments
    try:
        btc = payment_summary()
        existing["btc_summary"] = btc
        print(f"[sync] BTC balance: {btc['balance_btc']} BTC (${btc['balance_usd']})")
    except Exception as e:
        print(f"[sync] BTC fetch failed: {e}")

    existing["last_updated"] = datetime.now(timezone.utc).isoformat()

    SALES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SALES_FILE.write_text(json.dumps(existing, indent=2))
    print("[sync] data/sales.json updated")


if __name__ == "__main__":
    run()
