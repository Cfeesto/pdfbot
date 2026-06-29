"""
pinterest.py — auto-post a pin for each new PDF guide.
Pinterest API v5. Generates pin image with Pillow (no external hosting needed).

Required env vars:
  PINTEREST_TOKEN     — long-lived access token from developers.pinterest.com
  PINTEREST_BOARD_ID  — board ID (find in board URL)
"""

import os
import io
import base64
import requests
from PIL import Image, ImageDraw

BASE_URL = "https://api.pinterest.com/v5"
TOKEN    = os.environ.get("PINTEREST_TOKEN", "")
BOARD_ID = os.environ.get("PINTEREST_BOARD_ID", "")

# Pinterest optimal ratio is 2:3
PIN_W, PIN_H = 1000, 1500


def _get_font(size: int):
    """Load system font with graceful fallback."""
    from PIL import ImageFont
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _wrap(text: str, max_chars: int = 26) -> list[str]:
    words, lines, line = text.split(), [], []
    for w in words:
        if sum(len(x) + 1 for x in line) + len(w) > max_chars:
            if line:
                lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines


def _make_pin_image(title: str, subtitle: str, price: float) -> bytes:
    img  = Image.new("RGB", (PIN_W, PIN_H), color=(22, 33, 62))   # dark navy
    draw = ImageDraw.Draw(img)

    # Accent bar top
    draw.rectangle([0, 0, PIN_W, 14], fill=(99, 102, 241))

    # Price badge top-right
    f_badge = _get_font(36)
    badge   = f"${price:.2f}"
    draw.rounded_rectangle([PIN_W - 160, 30, PIN_W - 20, 82], radius=8, fill=(99, 102, 241))
    draw.text((PIN_W - 90, 56), badge, fill="white", font=f_badge, anchor="mm")

    # "INSTANT DOWNLOAD" pill
    f_pill = _get_font(26)
    draw.rounded_rectangle([30, 30, 260, 76], radius=8, fill=(0, 200, 83))
    draw.text((145, 53), "INSTANT DOWNLOAD", fill="white", font=f_pill, anchor="mm")

    # Title (large, centred, wrapped)
    f_title = _get_font(72)
    lines   = _wrap(title.replace("Complete Guide: ", ""), max_chars=20)
    y = PIN_H // 3
    for line in lines[:4]:
        draw.text((PIN_W // 2, y), line, fill="white", font=f_title, anchor="mm")
        y += 88

    # Subtitle
    if subtitle:
        f_sub = _get_font(34)
        sub   = subtitle[:80] + ("…" if len(subtitle) > 80 else "")
        draw.text((PIN_W // 2, y + 30), sub, fill=(180, 180, 220), font=f_sub, anchor="mm")

    # Bottom strip
    draw.rectangle([0, PIN_H - 90, PIN_W, PIN_H], fill=(16, 21, 62))
    f_footer = _get_font(30)
    draw.text((PIN_W // 2, PIN_H - 45), "Download at Gumroad · PDF Guide", fill=(140, 140, 200), font=f_footer, anchor="mm")

    # Accent bar bottom
    draw.rectangle([0, PIN_H - 12, PIN_W, PIN_H], fill=(99, 102, 241))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def post_pin(title: str, subtitle: str, price: float, gumroad_url: str, tags: list[str] = None) -> dict:
    """Create a Pinterest pin for a PDF product. Returns pin dict."""
    if not TOKEN or not BOARD_ID:
        raise RuntimeError("PINTEREST_TOKEN or PINTEREST_BOARD_ID not set")

    image_bytes = _make_pin_image(title, subtitle, price)
    image_b64   = base64.b64encode(image_bytes).decode()

    tag_str = " ".join(f"#{t}" for t in (tags or [])[:6])
    description = (
        f"{subtitle}\n\n"
        f"✅ Instant digital download\n"
        f"💡 Practical, actionable guide\n"
        f"💰 Only ${price:.2f}\n\n"
        f"{tag_str} #digitaldownload #ebook #guide #passiveincome"
    )[:500]

    r = requests.post(
        f"{BASE_URL}/pins",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={
            "board_id":    BOARD_ID,
            "title":       title[:100],
            "description": description,
            "link":        gumroad_url,
            "media_source": {
                "source_type":  "image_base64",
                "content_type": "image/png",
                "data":         image_b64,
            },
        },
    )
    r.raise_for_status()
    pin = r.json()
    print(f"[pinterest] Pinned: {title} → pin/{pin.get('id')}")
    return pin
