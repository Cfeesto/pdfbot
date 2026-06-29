"""
devto.py — publish a teaser article to Dev.to for each new PDF guide.
The article previews 3 chapters, then links to Gumroad for the full PDF.
This drives organic Google search traffic to your products.

Setup (1 min):
  1. Go to dev.to/settings/extensions -> scroll to DEV Community API Keys
  2. Generate key, copy it
  3. Add GitHub secret: DEVTO_API_KEY

Bonus: also posts to Hashnode if HASHNODE_TOKEN + HASHNODE_PUB_ID are set.
"""

import os
import requests

DEVTO_KEY       = os.environ.get("DEVTO_API_KEY", "")
HASHNODE_TOKEN  = os.environ.get("HASHNODE_TOKEN", "")
HASHNODE_PUB_ID = os.environ.get("HASHNODE_PUB_ID", "")


def _build_markdown(content: dict, price: float, gumroad_url: str) -> str:
    chapters = content.get("chapters", [])
    intro    = content.get("intro", "")
    tips     = content.get("tips", [])

    md = f"## Introduction\n\n{intro}\n\n"

    for ch in chapters[:3]:
        body_preview = ch["body"][:500]
        if len(ch["body"]) > 500:
            body_preview += "..."
        md += f"## {ch['heading']}\n\n{body_preview}\n\n"

    if tips:
        md += "## Quick Tips\n\n"
        md += "\n".join(f"- {t}" for t in tips[:3])
        md += "\n\n"

    md += (
        f"---\n\n"
        f"*This is a preview. The full guide includes all 5 chapters, "
        f"detailed examples, and a complete action plan.*\n\n"
        f"**[Get the complete PDF guide for ${price:.2f} →]({gumroad_url})**\n\n"
        f"Instant download. No subscription.\n"
    )
    return md


def publish_devto(title: str, content: dict, price: float,
                  gumroad_url: str, tags: list[str]) -> str:
    """Publish teaser article to Dev.to. Returns article URL."""
    if not DEVTO_KEY:
        raise RuntimeError("DEVTO_API_KEY not set")

    body_md  = _build_markdown(content, price, gumroad_url)
    tags_fmt = [t.lower().replace(" ", "")[:20] for t in tags[:4]]

    r = requests.post(
        "https://dev.to/api/articles",
        headers={"api-key": DEVTO_KEY, "Content-Type": "application/json"},
        json={"article": {
            "title":         title,
            "body_markdown": body_md,
            "published":     True,
            "tags":          tags_fmt,
        }},
    )
    r.raise_for_status()
    article = r.json()
    url = article.get("url", "")
    print(f"[devto] Published: {title} -> {url}")
    return url


def publish_hashnode(title: str, content: dict, price: float,
                     gumroad_url: str, tags: list[str]) -> str:
    """Publish same article to Hashnode. Returns article URL."""
    if not HASHNODE_TOKEN or not HASHNODE_PUB_ID:
        raise RuntimeError("HASHNODE_TOKEN or HASHNODE_PUB_ID not set")

    body_md  = _build_markdown(content, price, gumroad_url)
    tag_objs = [{"slug": t.lower().replace(" ", "-")[:20], "name": t[:20]} for t in tags[:5]]

    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post { url title }
      }
    }
    """
    variables = {"input": {
        "title":         title,
        "contentMarkdown": body_md,
        "publicationId": HASHNODE_PUB_ID,
        "tags":          tag_objs,
    }}

    r = requests.post(
        "https://gql.hashnode.com",
        headers={"Authorization": HASHNODE_TOKEN, "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
    )
    r.raise_for_status()
    data = r.json()
    url = (data.get("data", {}).get("publishPost", {}).get("post") or {}).get("url", "")
    print(f"[hashnode] Published: {title} -> {url}")
    return url
