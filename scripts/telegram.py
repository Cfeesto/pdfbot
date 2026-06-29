"""
telegram.py — post new PDF announcements to a Telegram channel.
Zero config: just a bot token from @BotFather and your channel ID.

Setup (2 min):
  1. Message @BotFather on Telegram → /newbot → copy token
  2. Add the bot as admin to your channel
  3. Add GitHub secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
     (channel ID format: @yourchannel  OR  -100123456789)
"""

import os
import requests

BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
API_BASE   = f"https://api.telegram.org/bot{BOT_TOKEN}"


def post_product(title: str, subtitle: str, price: float,
                 gumroad_url: str, etsy_url: str = "",
                 tags: list[str] = None, pin_image: bytes = None) -> dict:
    """
    Send a product announcement to the Telegram channel.
    If pin_image bytes are provided, sends as photo with caption.
    Otherwise sends a formatted text message.
    """
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set")

    tag_line = " ".join(f"#{t.replace(' ', '')}" for t in (tags or [])[:5])
    links    = f"[🛒 Buy on Gumroad]({gumroad_url})"
    if etsy_url:
        links += f"  ·  [🏪 Buy on Etsy]({etsy_url})"

    caption = (
        f"📄 *New Guide Available*\n\n"
        f"*{title}*\n"
        f"_{subtitle}_\n\n"
        f"💰 Only *${price:.2f}* — instant download\n\n"
        f"{links}\n\n"
        f"{tag_line}"
    )

    if pin_image:
        r = requests.post(
            f"{API_BASE}/sendPhoto",
            data={"chat_id": CHANNEL_ID, "caption": caption[:1024], "parse_mode": "Markdown"},
            files={"photo": ("cover.png", pin_image, "image/png")},
        )
    else:
        r = requests.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": caption[:4096], "parse_mode": "Markdown",
                  "disable_web_page_preview": False},
        )

    r.raise_for_status()
    result = r.json()
    print(f"[telegram] Posted: {title}")
    return result
