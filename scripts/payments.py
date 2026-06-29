"""
payments.py — Bitcoin payment tracking via blockchain.info public API.
No API key needed. Checks incoming transactions to the BTC address.
BTC_ADDRESS is set via environment variable (GitHub secret).
"""

import os
import requests
from datetime import datetime, timezone

BTC_ADDRESS = os.environ.get("BTC_ADDRESS", "")
BLOCKCHAIN_API = "https://blockchain.info"


def get_balance_btc() -> float:
    """Return current confirmed balance in BTC."""
    if not BTC_ADDRESS:
        return 0.0
    r = requests.get(
        f"{BLOCKCHAIN_API}/q/addressbalance/{BTC_ADDRESS}",
        params={"confirmations": 1},
        timeout=10,
    )
    r.raise_for_status()
    satoshis = int(r.text.strip())
    return satoshis / 1e8


def get_recent_transactions(limit: int = 10) -> list[dict]:
    """
    Return recent incoming transactions to the BTC address.
    Each dict: {txid, amount_btc, confirmed, timestamp_utc}
    """
    if not BTC_ADDRESS:
        return []
    r = requests.get(
        f"{BLOCKCHAIN_API}/rawaddr/{BTC_ADDRESS}",
        params={"limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()

    txs = []
    for tx in data.get("txs", [])[:limit]:
        # Sum outputs sent TO our address
        amount_sat = sum(
            o["value"] for o in tx.get("out", [])
            if o.get("addr") == BTC_ADDRESS
        )
        if amount_sat <= 0:
            continue

        ts = tx.get("time", 0)
        txs.append({
            "txid":          tx["hash"],
            "amount_btc":    amount_sat / 1e8,
            "confirmed":     tx.get("block_height") is not None,
            "timestamp_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None,
        })

    return txs


def get_btc_usd_price() -> float:
    """Current BTC/USD price from blockchain.info ticker."""
    try:
        r = requests.get(f"{BLOCKCHAIN_API}/ticker", timeout=5)
        return r.json()["USD"]["last"]
    except Exception:
        return 0.0


def payment_summary() -> dict:
    """Full summary for the dashboard."""
    txs   = get_recent_transactions(20)
    price = get_btc_usd_price()
    bal   = get_balance_btc()
    total_received = sum(t["amount_btc"] for t in txs if t["confirmed"])
    return {
        "address":        BTC_ADDRESS,
        "balance_btc":    bal,
        "balance_usd":    round(bal * price, 2),
        "btc_usd_price":  price,
        "total_received_btc": total_received,
        "total_received_usd": round(total_received * price, 2),
        "recent_txs":     txs,
    }


if __name__ == "__main__":
    summary = payment_summary()
    print(f"Balance: {summary['balance_btc']} BTC (${summary['balance_usd']})")
    print(f"Recent txs: {len(summary['recent_txs'])}")
