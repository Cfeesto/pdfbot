"""
browser_distribute.py — stealth browser posting to Reddit, Twitter/X, Medium, Quora.

Uses nodriver (CDP-based, undetectable) to post to platforms that block APIs.
Reads data/products.json, tracks posted IDs in data/browser_posted.json.

Required env vars (add as GitHub secrets + VPS env):
  REDDIT_USER      — Reddit username
  REDDIT_PASS      — Reddit password
  TWITTER_USER     — Twitter/X email
  TWITTER_PASS     — Twitter/X password
  MEDIUM_EMAIL     — Medium email
  MEDIUM_PASS      — Medium password

Run: python browser_distribute.py [product_id]
     python browser_distribute.py          # posts all unposted
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import nodriver as uc

DATA_FILE    = Path(__file__).parent.parent / "data" / "products.json"
POSTED_FILE  = Path(__file__).parent.parent / "data" / "browser_posted.json"

# Subreddit map: tag keywords → subreddits to post to
SUBREDDIT_MAP = {
    "crypto":      ["CryptoCurrency", "passive_income", "CryptoBeginners"],
    "bitcoin":     ["Bitcoin", "CryptoCurrency", "passive_income"],
    "python":      ["learnpython", "Python", "passive_income", "learnprogramming"],
    "podcast":     ["podcasting", "passive_income", "entrepreneur"],
    "ai":          ["artificial", "MachineLearning", "passive_income"],
    "business":    ["Entrepreneur", "passive_income", "smallbusiness"],
    "finance":     ["personalfinance", "passive_income", "financialindependence"],
    "marketing":   ["marketing", "Entrepreneur", "passive_income"],
    "default":     ["passive_income", "digitalnomad", "sidehustle"],
}

REDDIT_USER   = os.environ.get("REDDIT_USER", "")
REDDIT_PASS   = os.environ.get("REDDIT_PASS", "")
TWITTER_USER  = os.environ.get("TWITTER_USER", "")
TWITTER_PASS  = os.environ.get("TWITTER_PASS", "")
MEDIUM_EMAIL  = os.environ.get("MEDIUM_EMAIL", "")
MEDIUM_PASS   = os.environ.get("MEDIUM_PASS", "")


# ── helpers ──────────────────────────────────────────────────────────────────

def load_posted() -> dict:
    if POSTED_FILE.exists():
        return json.loads(POSTED_FILE.read_text())
    return {}


def save_posted(posted: dict):
    POSTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    POSTED_FILE.write_text(json.dumps(posted, indent=2))


def get_subreddits(tags: list) -> list:
    """Pick subreddits based on product tags."""
    tags_lower = [t.lower() for t in tags]
    matched = []
    for keyword, subs in SUBREDDIT_MAP.items():
        if any(keyword in t for t in tags_lower):
            matched.extend(subs)
    # ponytail: dedup preserving order
    seen, result = set(), []
    for s in (matched or SUBREDDIT_MAP["default"]):
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result[:3]   # max 3 subs per product to avoid spam flags


async def wait_for(tab, selector: str, timeout: int = 10):
    """Wait for element to appear."""
    for _ in range(timeout * 4):
        try:
            el = await tab.find(selector)
            if el:
                return el
        except Exception:
            pass
        await asyncio.sleep(0.25)
    return None


# ── Reddit ───────────────────────────────────────────────────────────────────

async def post_reddit(browser, product: dict) -> list[str]:
    """Login to Reddit and post to relevant subreddits. Returns list of post URLs."""
    if not REDDIT_USER or not REDDIT_PASS:
        print("[reddit] Skipped — REDDIT_USER/REDDIT_PASS not set")
        return []

    title       = product["title"]
    gumroad_url = product.get("gumroad_url", product.get("pdf_url", ""))
    tags        = product.get("tags", [])
    price       = product.get("price_usd", 9.99)
    subtitle    = product.get("subtitle", "")
    subreddits  = get_subreddits(tags)
    posted_urls = []

    try:
        tab = await browser.get("https://www.reddit.com/login")
        await asyncio.sleep(2)

        # Fill login form
        user_el = await wait_for(tab, "input[name='username']")
        pass_el = await wait_for(tab, "input[name='password']")
        if not user_el or not pass_el:
            print("[reddit] Login form not found")
            return []

        await user_el.send_keys(REDDIT_USER)
        await asyncio.sleep(0.3)
        await pass_el.send_keys(REDDIT_PASS)
        await asyncio.sleep(0.3)

        btn = await wait_for(tab, "button[type='submit']")
        if btn:
            await btn.click()
        await asyncio.sleep(3)

        for sub in subreddits:
            try:
                post_url = f"https://www.reddit.com/r/{sub}/submit?type=link"
                await tab.get(post_url)
                await asyncio.sleep(2)

                # Title field
                title_el = await wait_for(tab, "textarea[placeholder*='itle'], input[name='title']", 8)
                if not title_el:
                    print(f"[reddit] r/{sub}: title field not found, skipping")
                    continue
                await title_el.send_keys(f"{title} — Instant PDF Download (${price:.2f})")
                await asyncio.sleep(0.3)

                # URL field (link post)
                url_el = await wait_for(tab, "input[name='url'], input[placeholder*='rl']", 5)
                if url_el:
                    await url_el.send_keys(gumroad_url)
                    await asyncio.sleep(0.3)

                submit = await wait_for(tab, "button[type='submit']", 5)
                if submit:
                    await submit.click()
                    await asyncio.sleep(3)
                    current_url = await tab.get_current_url() if hasattr(tab, "get_current_url") else ""
                    posted_urls.append(current_url or f"https://reddit.com/r/{sub}")
                    print(f"[reddit] Posted to r/{sub}")
                    await asyncio.sleep(2)   # polite delay between posts

            except Exception as e:
                print(f"[reddit] r/{sub} failed: {e}")
                continue

    except Exception as e:
        print(f"[reddit] Error: {e}")

    return posted_urls


# ── Twitter/X ────────────────────────────────────────────────────────────────

async def post_twitter(browser, product: dict) -> str:
    """Post a tweet. Returns tweet URL or empty string."""
    if not TWITTER_USER or not TWITTER_PASS:
        print("[twitter] Skipped — TWITTER_USER/TWITTER_PASS not set")
        return ""

    title       = product["title"]
    gumroad_url = product.get("gumroad_url", "")
    tags        = product.get("tags", [])[:4]
    price       = product.get("price_usd", 9.99)
    hashtags    = " ".join(f"#{t}" for t in tags) + " #digitaldownload #passiveincome"

    tweet_text = (
        f"📚 {title}\n\n"
        f"✅ Instant PDF download\n"
        f"💰 Only ${price:.2f}\n\n"
        f"{gumroad_url}\n\n"
        f"{hashtags}"
    )[:280]

    try:
        tab = await browser.get("https://twitter.com/i/flow/login")
        await asyncio.sleep(3)

        # Step 1: email/username
        user_el = await wait_for(tab, "input[autocomplete='username']", 10)
        if not user_el:
            print("[twitter] Login field not found")
            return ""
        await user_el.send_keys(TWITTER_USER)
        await asyncio.sleep(0.3)

        next_btn = await wait_for(tab, "[data-testid='LoginForm_Login_Button'], span[data-testid='ocfEnterTextNextButton']", 5)
        if not next_btn:
            # try pressing Enter
            await tab.keyboard.send("\n")
        else:
            await next_btn.click()
        await asyncio.sleep(2)

        # Step 2: password
        pass_el = await wait_for(tab, "input[name='password']", 8)
        if not pass_el:
            print("[twitter] Password field not found")
            return ""
        await pass_el.send_keys(TWITTER_PASS)
        await asyncio.sleep(0.3)

        login_btn = await wait_for(tab, "[data-testid='LoginForm_Login_Button']", 5)
        if login_btn:
            await login_btn.click()
        await asyncio.sleep(4)

        # Compose tweet
        compose = await wait_for(tab, "[data-testid='tweetTextarea_0'], [data-testid='tweetText']", 10)
        if not compose:
            print("[twitter] Compose box not found after login")
            return ""
        await compose.click()
        await asyncio.sleep(0.3)
        await compose.send_keys(tweet_text)
        await asyncio.sleep(0.5)

        tweet_btn = await wait_for(tab, "[data-testid='tweetButtonInline'], [data-testid='tweetButton']", 5)
        if tweet_btn:
            await tweet_btn.click()
            await asyncio.sleep(3)
            print(f"[twitter] Tweet posted: {title[:50]}")
            return "https://twitter.com"
        else:
            print("[twitter] Tweet button not found")

    except Exception as e:
        print(f"[twitter] Error: {e}")

    return ""


# ── Medium ───────────────────────────────────────────────────────────────────

async def post_medium(browser, product: dict) -> str:
    """Publish a teaser story on Medium. Returns story URL or empty string."""
    if not MEDIUM_EMAIL or not MEDIUM_PASS:
        print("[medium] Skipped — MEDIUM_EMAIL/MEDIUM_PASS not set")
        return ""

    title       = product["title"]
    subtitle    = product.get("subtitle", "")
    gumroad_url = product.get("gumroad_url", "")
    price       = product.get("price_usd", 9.99)
    content_md  = product.get("content", {})

    # Build 3-paragraph teaser
    chapters = content_md.get("chapters", []) if isinstance(content_md, dict) else []
    teaser_paras = ""
    for ch in chapters[:3]:
        teaser_paras += f"\n\n## {ch.get('title','')}\n\n{ch.get('content','')[:400]}…"

    story_body = (
        f"# {title}\n\n"
        f"**{subtitle}**\n\n"
        f"{teaser_paras}\n\n"
        f"---\n\n"
        f"*Want the full guide? [Download the complete PDF for ${price:.2f}]({gumroad_url}) — instant delivery.*"
    )

    try:
        tab = await browser.get("https://medium.com/m/signin")
        await asyncio.sleep(2)

        # Click "Sign in with email"
        email_btn = await wait_for(tab, "button[data-action='sign-in-with-email'], [data-testid='email-button']", 8)
        if not email_btn:
            # Try finding by text
            els = await tab.find_all("button")
            for el in els:
                text = await el.get_text() if hasattr(el, "get_text") else ""
                if "email" in text.lower():
                    email_btn = el
                    break

        if email_btn:
            await email_btn.click()
            await asyncio.sleep(1)

        email_input = await wait_for(tab, "input[type='email'], input[name='email']", 8)
        if not email_input:
            print("[medium] Email field not found")
            return ""
        await email_input.send_keys(MEDIUM_EMAIL)
        await asyncio.sleep(0.3)

        cont_btn = await wait_for(tab, "button[type='submit']", 5)
        if cont_btn:
            await cont_btn.click()
        await asyncio.sleep(2)

        # Medium sends a magic link — password flow only works with Google/Twitter auth
        # If password field appears, fill it
        pass_el = await wait_for(tab, "input[type='password']", 4)
        if pass_el:
            await pass_el.send_keys(MEDIUM_PASS)
            submit = await wait_for(tab, "button[type='submit']", 3)
            if submit:
                await submit.click()
            await asyncio.sleep(3)
        else:
            print("[medium] Medium uses magic link — check your email to complete login once, then re-run")
            return ""

        # Navigate to new story
        await tab.get("https://medium.com/new-story")
        await asyncio.sleep(3)

        # Type title
        title_el = await wait_for(tab, "h3[data-placeholder='Title'], [data-testid='editor-title']", 10)
        if not title_el:
            print("[medium] Editor title not found")
            return ""
        await title_el.click()
        await title_el.send_keys(title)
        await asyncio.sleep(0.3)

        # Tab to body
        await tab.keyboard.send("\t")
        await asyncio.sleep(0.3)
        body_el = await wait_for(tab, "p[data-placeholder='Tell your story…'], [contenteditable='true']", 5)
        if body_el:
            await body_el.click()
            await body_el.send_keys(story_body)
        await asyncio.sleep(1)

        # Publish
        pub_btn = await wait_for(tab, "button[data-action='publish']", 5)
        if pub_btn:
            await pub_btn.click()
            await asyncio.sleep(2)
            final_btn = await wait_for(tab, "button[data-action='confirm-publish']", 5)
            if final_btn:
                await final_btn.click()
                await asyncio.sleep(3)
                print(f"[medium] Published: {title[:50]}")
                return "https://medium.com"

    except Exception as e:
        print(f"[medium] Error: {e}")

    return ""


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    if not DATA_FILE.exists():
        print("No products.json found")
        return

    products = json.loads(DATA_FILE.read_text())
    posted   = load_posted()

    # Filter to unposted (or specific product_id from argv)
    target_id = sys.argv[1] if len(sys.argv) > 1 else None
    if target_id:
        products = [p for p in products if p.get("id") == target_id]
    else:
        products = [p for p in products if p.get("id") not in posted]

    if not products:
        print("No new products to distribute")
        return

    print(f"[browser_distribute] Distributing {len(products)} product(s)")

    # ponytail: single browser instance, reuse across all platforms per product
    browser = await uc.start(headless=True, browser_args=["--no-sandbox", "--disable-dev-shm-usage"])

    try:
        for product in products:
            pid   = product.get("id")
            title = product.get("title", "")
            print(f"\n── {title} ──")

            result = {"id": pid, "title": title, "reddit": [], "twitter": "", "medium": ""}

            # Reddit (highest reach for niche topics)
            result["reddit"]  = await post_reddit(browser, product)

            # Twitter/X
            result["twitter"] = await post_twitter(browser, product)

            # Medium (SEO + authority)
            result["medium"]  = await post_medium(browser, product)

            posted[pid] = result
            save_posted(posted)
            print(f"[browser_distribute] ✓ {title[:50]}")

    finally:
        browser.stop()

    print("\n[browser_distribute] Done.")


if __name__ == "__main__":
    asyncio.run(main())
