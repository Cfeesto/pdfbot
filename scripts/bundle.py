"""
bundle.py — weekly mega-bundle: zip the latest N PDFs → sell on Gumroad at $19.99.
Run by .github/workflows/bundle-weekly.yml every Monday.

Flow:
  1. Read data/products.json
  2. Download PDFs from GitHub Releases (gh CLI)
  3. Zip them all
  4. Upload zip to a new GitHub Release
  5. Create/update a Gumroad bundle listing
"""

import json
import os
import subprocess
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from gumroad import create_product

DATA_FILE = Path(__file__).parent.parent / "data" / "products.json"
BUNDLE_SIZE   = int(os.environ.get("BUNDLE_SIZE", "5"))
BUNDLE_PRICE  = float(os.environ.get("BUNDLE_PRICE_USD", "19.99"))
GH_REPO       = os.environ.get("GITHUB_REPOSITORY", "")


def _download_pdf(release_tag: str, filename: str, dest_dir: str) -> str | None:
    """Download a PDF from a GitHub Release using gh CLI. Returns local path or None."""
    dest = os.path.join(dest_dir, filename)
    result = subprocess.run(
        ["gh", "release", "download", release_tag, "--pattern", filename,
         "--dir", dest_dir, "--clobber"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[bundle] Could not download {filename}: {result.stderr.strip()}")
        return None
    return dest if os.path.exists(dest) else None


def _upload_bundle(zip_path: str, tag: str) -> str:
    filename = os.path.basename(zip_path)
    subprocess.run(
        ["gh", "release", "create", tag, "--title", tag,
         "--notes", "Auto-generated PDF bundle", "--prerelease"],
        capture_output=True,
    )
    result = subprocess.run(
        ["gh", "release", "upload", tag, zip_path, "--clobber"],
        capture_output=True, text=True, check=True,
    )
    return f"https://github.com/{GH_REPO}/releases/download/{tag}/{filename}"


def run():
    if not DATA_FILE.exists():
        print("[bundle] No products.json found, skipping.")
        return

    products = json.loads(DATA_FILE.read_text())
    if not products:
        print("[bundle] No products yet.")
        return

    # Take the most recent BUNDLE_SIZE products that have a pdf_url
    candidates = [p for p in reversed(products) if p.get("pdf_url")][:BUNDLE_SIZE]
    if len(candidates) < 2:
        print(f"[bundle] Only {len(candidates)} PDF(s) available, need at least 2. Skipping.")
        return

    print(f"[bundle] Building bundle from {len(candidates)} PDFs…")

    with tempfile.TemporaryDirectory() as tmpdir:
        local_pdfs = []
        for p in candidates:
            pdf_url  = p["pdf_url"]
            # Extract tag and filename from GitHub release URL
            # e.g. https://github.com/user/repo/releases/download/TAG/file.pdf
            parts    = pdf_url.split("/releases/download/")
            if len(parts) != 2:
                continue
            tag_file = parts[1].split("/", 1)
            if len(tag_file) != 2:
                continue
            tag, filename = tag_file
            local = _download_pdf(tag, filename, tmpdir)
            if local:
                local_pdfs.append((p["title"], local))

        if len(local_pdfs) < 2:
            print("[bundle] Not enough PDFs downloaded, skipping.")
            return

        # Create zip
        timestamp  = datetime.now(timezone.utc).strftime("%Y%m%d")
        zip_name   = f"PDF_Bundle_{timestamp}_{len(local_pdfs)}_Guides.zip"
        zip_path   = os.path.join(tmpdir, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for title, path in local_pdfs:
                arcname = os.path.basename(path)
                zf.write(path, arcname)
        print(f"[bundle] Zipped {len(local_pdfs)} PDFs → {zip_name}")

        # Upload to GitHub Release
        bundle_tag   = f"bundle-{timestamp}"
        download_url = _upload_bundle(zip_path, bundle_tag)
        print(f"[bundle] Uploaded: {download_url}")

    # Build Gumroad listing
    titles_list = "\n".join(f"• {t}" for t, _ in local_pdfs)
    description = (
        f"Get {len(local_pdfs)} premium PDF guides in one bundle — instant download.\n\n"
        f"Included guides:\n{titles_list}\n\n"
        f"Each guide is packed with actionable, practical advice.\n"
        f"#bundle #digitaldownload #guides #passiveincome #ebook"
    )
    title = f"PDF Bundle: {len(local_pdfs)} Premium Guides ({timestamp})"

    try:
        product = create_product(
            title        = title,
            description  = description,
            pdf_path     = "",          # not uploading — using download_url
            price_usd    = BUNDLE_PRICE,
            btc_address  = os.environ.get("BTC_ADDRESS", ""),
            download_url = download_url,
        )
        gumroad_url = product.get("short_url", "")
        print(f"[bundle] Gumroad bundle: {gumroad_url}")
    except Exception as e:
        print(f"[bundle] Gumroad failed: {e}")
        gumroad_url = ""

    # Append bundle record to products.json
    products = json.loads(DATA_FILE.read_text())
    products.append({
        "id":          bundle_tag,
        "topic":       f"Bundle: {len(local_pdfs)} guides",
        "country":     "US",
        "title":       title,
        "subtitle":    f"{len(local_pdfs)} PDF guides, instant download",
        "tags":        ["bundle", "ebook", "guide", "digitaldownload"],
        "price_usd":   BUNDLE_PRICE,
        "pdf_url":     download_url,
        "gumroad_url": gumroad_url,
        "gumroad_id":  "",
        "etsy_url":    "",
        "created_at":  datetime.now(timezone.utc).isoformat(),
        "is_bundle":   True,
    })
    DATA_FILE.write_text(json.dumps(products, indent=2))
    print(f"[bundle] Done — bundle of {len(local_pdfs)} PDFs at ${BUNDLE_PRICE}")


if __name__ == "__main__":
    run()
