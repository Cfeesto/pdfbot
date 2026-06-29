"""
trends.py — fetch trending topics via Google Trends RSS feed (public, no auth).
RSS URL: https://trends.google.com/trends/trendingsearches/daily/rss?geo=US
No pytrends needed — plain requests + XML parsing.
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

COUNTRIES = [
    "US", "GB", "AU", "CA", "NG", "ZA", "IN", "PH",
    "GH", "KE", "SG", "NZ", "IE",
]

DATA_FILE = Path(__file__).parent.parent / "data" / "products.json"

RSS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; pdf-bot/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}


def _already_generated(topic: str) -> bool:
    if not DATA_FILE.exists():
        return False
    products = json.loads(DATA_FILE.read_text())
    existing = {p["topic"].lower() for p in products}
    return topic.lower() in existing


def _fetch_country(geo: str) -> list[str]:
    """Fetch trending topics for one country via RSS. Returns list of topic strings."""
    try:
        r = requests.get(RSS_URL.format(geo=geo), headers=HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        # RSS items are under channel/item, title is the trending topic
        topics = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            if title:
                topics.append(title)
        return topics
    except Exception as e:
        print(f"[trends] {geo} failed: {e}")
        return []


def fetch_trends(max_topics: int = 5) -> list[dict]:
    """
    Returns up to max_topics new trending topics across all countries.
    Each item: {"topic": str, "country": str}
    """
    results = []
    seen = set()

    for geo in COUNTRIES:
        if len(results) >= max_topics:
            break
        topics = _fetch_country(geo)
        for topic in topics:
            if len(results) >= max_topics:
                break
            if not topic or topic.lower() in seen:
                continue
            if _already_generated(topic):
                continue
            seen.add(topic.lower())
            results.append({"topic": topic, "country": geo})
        time.sleep(1)

    return results


if __name__ == "__main__":
    topics = fetch_trends(max_topics=5)
    for t in topics:
        print(t)
