#!/usr/bin/env python3
"""
Regenerates the Reading Constellation project from a Goodreads CSV export.

Usage:
    python3 scripts/update_reading_constellation.py [path/to/goodreads_export.csv]

Defaults to ~/Desktop/goodreads_library_export.csv if no path is given.
To re-export from Goodreads: My Books -> Import/Export -> Export Library.

Rebuilds the full node/link graph (books, authors, recency-based radius,
and review text) from scratch each run, so newly-read books, updated
ratings, and new reviews all show up automatically. The visualization
code itself (layout, force simulation, sidebar) is untouched.
"""
import csv
import json
import re
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
PAGE_PATH = SITE_ROOT / "projects" / "reading-constellation.html"
DESKTOP_COPY_PATH = Path.home() / "Desktop" / "reading-constellation.html"
DEFAULT_CSV = Path.home() / "Desktop" / "goodreads_library_export.csv"

DATA_BLOCK_RE = re.compile(
    r"(// READING_CONSTELLATION_DATA_START\n).*(\n// READING_CONSTELLATION_DATA_END)",
    re.S,
)

TAG_PLACEHOLDERS = [
    (re.compile(r"<br\s*/?>", re.I), "\x00BR\x00"),
    (re.compile(r"<b>", re.I), "\x00B1\x00"),
    (re.compile(r"</b>", re.I), "\x00B2\x00"),
    (re.compile(r"<i>", re.I), "\x00I1\x00"),
    (re.compile(r"</i>", re.I), "\x00I2\x00"),
    (re.compile(r"<u>", re.I), "\x00U1\x00"),
    (re.compile(r"</u>", re.I), "\x00U2\x00"),
    (re.compile(r"<spoiler>", re.I), "\x00SP1\x00"),
    (re.compile(r"</spoiler>", re.I), "\x00SP2\x00"),
]
RESTORE = {
    "\x00BR\x00": "<br>",
    "\x00B1\x00": "<b>",
    "\x00B2\x00": "</b>",
    "\x00I1\x00": "<i>",
    "\x00I2\x00": "</i>",
    "\x00U1\x00": "<u>",
    "\x00U2\x00": "</u>",
    "\x00SP1\x00": '<span class="spoiler" onclick="this.classList.toggle(\'revealed\')">',
    "\x00SP2\x00": "</span>",
}


def sanitize_review(raw):
    text = raw
    for pattern, placeholder in TAG_PLACEHOLDERS:
        text = pattern.sub(placeholder, text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for placeholder, real in RESTORE.items():
        text = text.replace(placeholder, real)
    return text.strip()


def load_read_books(csv_path):
    books = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Exclusive Shelf", "").strip() != "read":
                continue
            date_read = row["Date Read"].strip()
            date_added = row["Date Added"].strip()
            effective_date = (date_read or date_added).replace("/", "-")
            books.append(
                {
                    "id": "b" + row["Book Id"].strip(),
                    "title": row["Title"].strip(),
                    "author": row["Author"].strip(),
                    "rating": int(row["My Rating"] or 0),
                    "dateRead": effective_date,
                    "dateSource": "read" if date_read else "added",
                    "pages": row["Number of Pages"].strip(),
                    "review": sanitize_review(row.get("My Review", "").strip()),
                }
            )
    return books


def build_graph(books):
    # oldest first: this fixes both the radius scale (1.0=oldest, 0.0=newest)
    # and the order authors are first encountered in (-> their author id)
    books.sort(key=lambda b: b["dateRead"])
    n = len(books)

    author_ids = {}
    nodes = []
    links = []

    for i, b in enumerate(books):
        radius = 1.0 if n == 1 else 1 - i / (n - 1)
        if b["author"] not in author_ids:
            author_ids[b["author"]] = f"a{len(author_ids)}"
        author_id = author_ids[b["author"]]

        node = {
            "id": b["id"],
            "type": "book",
            "title": b["title"],
            "author": b["author"],
            "authorId": author_id,
            "rating": b["rating"],
            "dateRead": b["dateRead"],
            "dateSource": b["dateSource"],
            "radius": radius,
            "pages": b["pages"],
        }
        if b["review"]:
            node["review"] = b["review"]
        nodes.append(node)
        links.append({"source": b["id"], "target": author_id})

    author_books = {}
    for node in nodes:
        author_books.setdefault(node["authorId"], []).append(node)

    for name, author_id in author_ids.items():
        their_books = author_books[author_id]
        nodes.append(
            {
                "id": author_id,
                "type": "author",
                "name": name,
                "radius": min(b["radius"] for b in their_books),
                "bookCount": len(their_books),
            }
        )

    return {"nodes": nodes, "links": links}


def update_page(data):
    html = PAGE_PATH.read_text(encoding="utf-8")
    new_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    replacement = (
        r"\g<1>const __DATA__ = " + new_data.replace("\\", "\\\\") + r";\g<2>"
    )
    new_html, count = DATA_BLOCK_RE.subn(replacement, html)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one READING_CONSTELLATION_DATA block in {PAGE_PATH}, found {count}"
        )
    PAGE_PATH.write_text(new_html, encoding="utf-8")
    if DESKTOP_COPY_PATH.exists():
        DESKTOP_COPY_PATH.write_text(new_html, encoding="utf-8")


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        sys.exit(f"CSV not found: {csv_path}")

    books = load_read_books(csv_path)
    data = build_graph(books)
    update_page(data)

    book_count = sum(1 for n in data["nodes"] if n["type"] == "book")
    author_count = sum(1 for n in data["nodes"] if n["type"] == "author")
    with_review = sum(1 for n in data["nodes"] if n["type"] == "book" and "review" in n)

    print(f"Read {book_count} books by {author_count} authors from {csv_path}")
    print(f"{with_review} books have review text")
    print(f"Wrote data to {PAGE_PATH}")
    print("\nDon't forget to commit, push, and let GitHub Pages redeploy.")


if __name__ == "__main__":
    main()
