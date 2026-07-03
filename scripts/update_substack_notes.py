#!/usr/bin/env python3
"""
Regenerates the "From my Substack" post list on notes.html from the
Substack RSS feed. Run this periodically (e.g. whenever you publish a
new post) to refresh the list — Substack doesn't support a live
cross-site embed of post content, so this bakes a static snapshot in
at build time instead.

Usage:
    python3 scripts/update_substack_notes.py
"""
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

FEED_URL = "https://whatsupwithevan.substack.com/feed"
MAX_POSTS = 15

SITE_ROOT = Path(__file__).resolve().parent.parent
PAGE_PATH = SITE_ROOT / "notes.html"

LIST_BLOCK_RE = re.compile(
    r"(<!-- SUBSTACK_POSTS_START -->\n).*(\n\s*<!-- SUBSTACK_POSTS_END -->)",
    re.S,
)


def fetch_posts():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        xml_bytes = resp.read()

    root = ET.fromstring(xml_bytes)
    posts = []
    for item in root.findall("./channel/item")[:MAX_POSTS]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        try:
            pub_date = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z")
            date_str = pub_date.strftime("%B %Y")
        except ValueError:
            date_str = ""
        if title and link:
            posts.append({"title": title, "link": link, "date": date_str})
    return posts


def render_list(posts):
    lines = []
    for p in posts:
        lines.append("  <li>")
        lines.append(f'    <a href="{html.escape(p["link"])}">{html.escape(p["title"])}</a>')
        if p["date"]:
            lines.append(f'    <div style="color: var(--ink-soft); font-size: 0.9rem;">{p["date"]}</div>')
        lines.append("  </li>")
    return "\n".join(lines)


def update_page(posts):
    html_text = PAGE_PATH.read_text(encoding="utf-8")
    replacement = r"\g<1>" + render_list(posts).replace("\\", "\\\\") + r"\g<2>"
    new_html, count = LIST_BLOCK_RE.subn(replacement, html_text)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one SUBSTACK_POSTS block in {PAGE_PATH}, found {count}"
        )
    PAGE_PATH.write_text(new_html, encoding="utf-8")


def main():
    try:
        posts = fetch_posts()
    except Exception as e:
        sys.exit(f"Failed to fetch/parse the Substack feed: {e}")

    if not posts:
        sys.exit("No posts found in the feed - aborting rather than wiping the list.")

    update_page(posts)
    print(f"Wrote {len(posts)} posts to {PAGE_PATH}")
    print("\nDon't forget to commit, push, and let GitHub Pages redeploy.")


if __name__ == "__main__":
    main()
