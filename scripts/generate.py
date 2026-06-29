"""
generate.py — main orchestrator.
Called by GitHub Actions trend-scan.yml every hour.

Flow:
  1. Fetch trending topics (Google Trends, multi-country)
  2. For each new topic → generate content (Groq) → build PDF
  3. Upload PDF to GitHub Release
  4. List product on Gumroad
  5. Update data/products.json
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from trends      import fetch_trends
from content     import generate_content, generate_description
from pdf_builder import build_pdf
from gumroad     import create_product

DATA_FILE   = Path(__file__).parent.parent / "data" / "products.json"
OUTPUT_DIR  = Path("/tmp/pdfs")
BTC_ADDRESS = os.environ.get("BTC_ADDRESS", "")
PRICE_USD   = float(os.environ.get("PDF_PRICE_USD", "4.99"))
MAX_TOPICS  = int(os.environ.get("MAX_TOPICS", "3"))


def load_products() -> list:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []


def save_products(products: list):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(products, indent=2))


def upload_to_github_release(pdf_path: str, tag: str) -> str:
    """
    Upload PDF as a GitHub Release asset. Returns download URL.
    Uses gh CLI which is available in GitHub Actions runners.
    """
    filename = Path(pdf_path).name
    try:
        # Create release if it doesn't exist
        subprocess.run(
            ["gh", "release", "create", tag, "--title", tag,
             "--notes", f"Auto-generated PDF: {tag}", "--prerelease"],
            capture_output=True,
        )
        # Upload asset
        result = subprocess.run(
            ["gh", "release", "upload", tag, pdf_path, "--clobber"],
            capture_output=True, text=True, check=True,
        )
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        return f"https://github.com/{repo}/releases/download/{tag}/{filename}"
    except subprocess.CalledProcessError as e:
        print(f"[release] Upload failed: {e.stderr}")
        return ""


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    products  = load_products()
    topics    = fetch_trends(max_topics=MAX_TOPICS)

    if not topics:
        print("[generate] No new trending topics found.")
        return

    new_products = []

    for item in topics:
        topic   = item["topic"]
        country = item["country"]
        print(f"\n[generate] Processing: '{topic}' ({country})")

        try:
            # 1. Generate content
            content = generate_content(topic, country)
            print(f"[generate] Content ready: {content['title']}")

            # 2. Build PDF
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in topic)
            safe_name = safe_name.replace(" ", "_")[:50]
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
            filename  = f"{safe_name}_{timestamp}.pdf"
            pdf_path  = str(OUTPUT_DIR / filename)

            build_pdf(content, pdf_path, btc_address=BTC_ADDRESS)
            print(f"[generate] PDF built: {filename}")

            # 3. Upload to GitHub Release
            tag         = f"pdf-{safe_name.lower()}-{timestamp}"
            download_url = upload_to_github_release(pdf_path, tag)

            # 4. List on Gumroad
            description = generate_description(content)
            gumroad_product = {}
            try:
                gumroad_product = create_product(
                    title       = content["title"],
                    description = description,
                    pdf_path    = pdf_path,
                    price_usd   = PRICE_USD,
                    btc_address = BTC_ADDRESS,
                )
            except Exception as e:
                print(f"[gumroad] Failed: {e}")

            # 5. Record
            record = {
                "id":           tag,
                "topic":        topic,
                "country":      country,
                "title":        content["title"],
                "subtitle":     content["subtitle"],
                "tags":         content.get("tags", []),
                "price_usd":    PRICE_USD,
                "pdf_url":      download_url,
                "gumroad_url":  gumroad_product.get("short_url", ""),
                "gumroad_id":   gumroad_product.get("id", ""),
                "created_at":   datetime.now(timezone.utc).isoformat(),
            }
            new_products.append(record)
            products.append(record)
            print(f"[generate] Done: {content['title']}")

            time.sleep(2)   # be polite to APIs

        except Exception as e:
            print(f"[generate] ERROR for '{topic}': {e}")
            continue

    save_products(products)
    print(f"\n[generate] Created {len(new_products)} new PDF(s). Total: {len(products)}")

    # Print summary for GitHub Actions step output
    for p in new_products:
        print(f"::notice title=New PDF::{p['title']} — {p.get('gumroad_url', 'no gumroad url')}")


if __name__ == "__main__":
    run()
