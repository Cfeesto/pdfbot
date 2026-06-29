"""
trends.py — fetch trending topics by country via Google Trends.
Returns a list of (topic, country_code) tuples, deduped against
already-generated products to avoid duplicate PDFs.
"""

import json
import os
import time
from pathlib import Path
from pytrends.request import TrendReq

# Countries to scan (ISO 3166-1 alpha-2)
COUNTRIES = [
    "US", "GB", "AU", "CA", "NG", "ZA", "IN", "PH",
    "GH", "KE", "SG", "NZ", "IE", "JM", "TT",
]

DATA_FILE = Path(__file__).parent.parent / "data" / "products.json"


def _already_generated(topic: str) -> bool:
    """Avoid re-generating a PDF for a topic we already covered."""
    if not DATA_FILE.exists():
        return False
    products = json.loads(DATA_FILE.read_text())
    existing = {p["topic"].lower() for p in products}
    return topic.lower() in existing


def fetch_trends(max_topics: int = 5) -> list[dict]:
    """
    Returns up to max_topics new trending topics across all countries.
    Each item: {"topic": str, "country": str}
    """
    trends = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
    results = []
    seen = set()

    for geo in COUNTRIES:
        if len(results) >= max_topics:
            break
        try:
            df = trends.trending_searches(pn=_geo_to_pn(geo))
            for topic in df[0].tolist():
                topic = str(topic).strip()
                if not topic or topic.lower() in seen:
                    continue
                if _already_generated(topic):
                    continue
                seen.add(topic.lower())
                results.append({"topic": topic, "country": geo})
                if len(results) >= max_topics:
                    break
            time.sleep(1)  # polite rate limit
        except Exception as e:
            print(f"[trends] {geo} failed: {e}")
            continue

    return results


def _geo_to_pn(geo: str) -> str:
    """pytrends uses country name strings, not ISO codes."""
    mapping = {
        "US": "united_states", "GB": "united_kingdom", "AU": "australia",
        "CA": "canada", "NG": "nigeria", "ZA": "south_africa", "IN": "india",
        "PH": "philippines", "GH": "ghana", "KE": "kenya", "SG": "singapore",
        "NZ": "new_zealand", "IE": "ireland", "JM": "jamaica", "TT": "trinidad_and_tobago",
    }
    return mapping.get(geo, "united_states")


if __name__ == "__main__":
    topics = fetch_trends(max_topics=3)
    for t in topics:
        print(t)
