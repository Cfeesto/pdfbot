"""
reddit_post.py — post PDF products to relevant subreddits via Reddit API (PRAW).

Doesn't need residential IP. Free tier supports 100 req/min.

Setup (one-time):
  1. Go to https://www.reddit.com/prefs/apps → "create another app" → script type
  2. Set redirect URI to http://localhost:8080
  3. Save CLIENT_ID and CLIENT_SECRET as GitHub secrets / VPS env vars

Required env vars:
  REDDIT_CLIENT_ID     — app client id
  REDDIT_CLIENT_SECRET — app client secret
  REDDIT_USER          — your reddit username
  REDDIT_PASS          — your reddit password
"""

import os
import praw

CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER   = os.environ.get("REDDIT_USER", "")
REDDIT_PASS   = os.environ.get("REDDIT_PASS", "")

SUBREDDIT_MAP = {
    "crypto":    ["CryptoCurrencyBeginners", "passive_income"],
    "bitcoin":   ["Bitcoin", "passive_income"],
    "python":    ["learnpython", "passive_income"],
    "podcast":   ["podcasting", "passive_income"],
    "ai":        ["ArtificialIntelligence", "passive_income"],
    "business":  ["Entrepreneur", "passive_income"],
    "finance":   ["personalfinance", "passive_income"],
    "marketing": ["marketing", "passive_income"],
    "default":   ["passive_income", "sidehustle"],
}


def _get_subreddits(tags: list) -> list[str]:
    tags_lower = [t.lower() for t in tags]
    matched = []
    for kw, subs in SUBREDDIT_MAP.items():
        if any(kw in t for t in tags_lower):
            matched.extend(subs)
    seen, result = set(), []
    for s in (matched or SUBREDDIT_MAP["default"]):
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result[:2]   # max 2 to stay under spam radar


def post_product(title: str, subtitle: str, price: float, gumroad_url: str, tags: list) -> list[str]:
    if not all([CLIENT_ID, CLIENT_SECRET, REDDIT_USER, REDDIT_PASS]):
        raise RuntimeError("REDDIT_CLIENT_ID / CLIENT_SECRET / USER / PASS not set")

    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        username=REDDIT_USER,
        password=REDDIT_PASS,
        user_agent=f"pdf-bot/1.0 by u/{REDDIT_USER}",
    )

    post_title = f"{title} — Complete PDF Guide (${price:.2f}, instant download)"
    posted = []

    for sub_name in _get_subreddits(tags):
        try:
            sub  = reddit.subreddit(sub_name)
            post = sub.submit_link(title=post_title, url=gumroad_url)
            # Add a comment with more context
            post.reply(
                f"**{subtitle}**\n\n"
                f"This is a comprehensive PDF guide covering everything you need to know.\n\n"
                f"✅ Instant download · 💰 ${price:.2f} · No subscription\n\n"
                f"Happy to answer questions in the comments!"
            )
            posted.append(f"https://reddit.com{post.permalink}")
            print(f"[reddit] Posted to r/{sub_name}: {post.permalink}")
        except Exception as e:
            print(f"[reddit] r/{sub_name} failed: {e}")

    return posted
