"""
discord_post.py — post new PDF announcements to a Discord channel via webhook.
Truly zero config: just a webhook URL, no registration anywhere.

Setup (1 min):
  1. Open your Discord server, channel settings, Integrations, Webhooks, New Webhook
  2. Copy webhook URL
  3. Add GitHub secret: DISCORD_WEBHOOK_URL
"""

import os
import requests

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

EMBED_COLOR = 0x6366F1


def post_product(title: str, subtitle: str, price: float,
                 gumroad_url: str, etsy_url: str = "",
                 tags: list[str] = None) -> None:
    if not WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL not set")

    tag_str = " ".join(f"`#{t}`" for t in (tags or [])[:6])

    fields = [
        {"name": "Price",   "value": f"${price:.2f}",              "inline": True},
        {"name": "Gumroad", "value": f"[Buy now]({gumroad_url})",   "inline": True},
    ]
    if etsy_url:
        fields.append({"name": "Etsy", "value": f"[Buy on Etsy]({etsy_url})", "inline": True})

    r = requests.post(WEBHOOK_URL, json={
        "username": "PDF Bot",
        "embeds": [{
            "title":       title,
            "description": f"{subtitle}\n\nInstant digital download.\n\n{tag_str}",
            "color":       EMBED_COLOR,
            "fields":      fields,
            "footer":      {"text": "PDF Bot - New guide just dropped"},
        }]
    })
    r.raise_for_status()
    print(f"[discord] Posted: {title}")
