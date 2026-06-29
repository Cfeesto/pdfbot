"""
trends.py — trending topics from Reddit public JSON API + evergreen fallback.
Reddit's API works from any IP with no auth. Google Trends blocks Actions runners.
Evergreen topics always sell regardless of news cycle.
"""

import json
import random
import time
from pathlib import Path
import requests

DATA_FILE = Path(__file__).parent.parent / "data" / "products.json"

HEADERS = {"User-Agent": "pdf-bot/1.0 (guide generator)"}

# Subreddits that surface genuinely useful, sellable topics
SUBREDDITS = [
    "entrepreneur", "personalfinance", "productivity",
    "learnprogramming", "freelance", "digitalnomad",
    "passiveincome", "investing", "careerguidance", "Fitness",
]

# Evergreen topics — always sell, always relevant
EVERGREEN = [
    "How to Start Freelancing in 2025",
    "Passive Income Guide: 10 Real Methods",
    "ChatGPT Prompts for Business",
    "How to Build a Personal Brand Online",
    "Crypto for Beginners: Complete Guide",
    "Remote Work Productivity System",
    "How to Start Dropshipping",
    "Side Hustle Ideas That Actually Work",
    "Digital Marketing for Small Business",
    "How to Save Money Fast: 30-Day Plan",
    "Python for Beginners: Get Paid to Code",
    "Email Marketing That Converts",
    "How to Sell on Etsy: Complete Guide",
    "YouTube Channel Growth Secrets",
    "Fitness Home Workout 12-Week Plan",
    "How to Write and Sell Ebooks",
    "Stock Market Investing Basics",
    "How to Start a Podcast for Profit",
    "Social Media Content Strategy",
    "Budget Travel Guide: See the World for Less",
]


def _already_generated(topic: str) -> bool:
    if not DATA_FILE.exists():
        return False
    products = json.loads(DATA_FILE.read_text())
    existing = {p["topic"].lower() for p in products}
    return topic.lower() in existing


def _fetch_reddit_topics() -> list[str]:
    """Pull hot post titles from curated subreddits — no auth, works from any IP."""
    topics = []
    for sub in SUBREDDITS:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json?limit=5",
                headers=HEADERS, timeout=10,
            )
            if r.status_code != 200:
                continue
            posts = r.json()["data"]["children"]
            for p in posts:
                title = p["data"].get("title", "").strip()
                # Skip memes/images/questions — keep educational titles
                if len(title) > 15 and not title.startswith("[") and "?" not in title[:5]:
                    topics.append(title)
            time.sleep(0.5)
        except Exception as e:
            print(f"[trends] r/{sub} failed: {e}")
    return topics


def _clean_reddit_title(title: str) -> str:
    """Turn a Reddit post title into a guide title."""
    # Trim trailing punctuation, normalize
    title = title.rstrip(".,!?").strip()
    if not title.lower().startswith("how"):
        title = f"Complete Guide: {title}"
    return title


def fetch_trends(max_topics: int = 5) -> list[dict]:
    """
    Returns up to max_topics new topics to generate PDFs for.
    Priority: Reddit trending → evergreen fallback.
    Each item: {"topic": str, "country": str}
    """
    results = []
    seen = set()

    # 1. Try Reddit
    raw = _fetch_reddit_topics()
    for raw_title in raw:
        if len(results) >= max_topics:
            break
        topic = _clean_reddit_title(raw_title)
        if topic.lower() in seen or _already_generated(topic):
            continue
        seen.add(topic.lower())
        results.append({"topic": topic, "country": "US"})

    # 2. Fill remaining from evergreen (shuffled so we don't repeat same order)
    if len(results) < max_topics:
        pool = [t for t in EVERGREEN if not _already_generated(t) and t.lower() not in seen]
        random.shuffle(pool)
        for topic in pool:
            if len(results) >= max_topics:
                break
            results.append({"topic": topic, "country": "US"})

    return results


if __name__ == "__main__":
    topics = fetch_trends(max_topics=5)
    for t in topics:
        print(t)
