#!/usr/bin/env python3
"""
Regenerates the Favorite Words project from a Goodreads CSV export.

Usage:
    python3 scripts/update_favorite_words.py [path/to/goodreads_export.csv]

Defaults to ~/Desktop/goodreads_library_export.csv if no path is given.
To re-export from Goodreads: My Books -> Import/Export -> Export Library.

Requires:
    pip3 install wordfreq
    /usr/share/dict/words (present by default on macOS)
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import wordfreq

SITE_ROOT = Path(__file__).resolve().parent.parent
PAGE_PATH = SITE_ROOT / "projects" / "favorite-words.html"
DICT_PATH = Path("/usr/share/dict/words")
DEFAULT_CSV = Path.home() / "Desktop" / "goodreads_library_export.csv"

MIN_COUNT = 1
MIN_RATIO = 1.0  # only words used *more* than typical English count as "favorites"

TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[A-Za-z']+")
DATA_BLOCK_RE = re.compile(
    r"(// FAVORITE_WORDS_DATA_START\n).*(\n// FAVORITE_WORDS_DATA_END)", re.S
)


def load_dictionary():
    words = set()
    with open(DICT_PATH, encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip()
            if w and w.islower():
                words.add(w)
    return words


def extract_review_text(csv_path):
    texts = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get("My Review", "").strip()
            if raw:
                texts.append(TAG_RE.sub(" ", raw))
    return texts


def tokenize(text):
    tokens = []
    for match in WORD_RE.finditer(text):
        raw = match.group().strip("'")
        if len(raw) >= 2:
            tokens.append((raw.lower(), raw[0].isupper()))
    return tokens


def compute_word_scores(csv_path):
    dictionary = load_dictionary()
    texts = extract_review_text(csv_path)

    counts = Counter()
    capitalized_counts = Counter()
    for text in texts:
        for word, was_cap in tokenize(text):
            counts[word] += 1
            if was_cap:
                capitalized_counts[word] += 1

    total_words = sum(counts.values())

    scored = []
    for word, count in counts.items():
        if count < MIN_COUNT:
            continue
        if word not in dictionary:
            continue
        # likely a proper noun (brand/title/name) coinciding with an
        # unrelated dictionary entry — skip if usually capitalized
        if capitalized_counts[word] / count > 0.5:
            continue
        baseline = wordfreq.word_frequency(word, "en")
        if baseline == 0:
            continue
        ratio = (count / total_words) / baseline
        if ratio < MIN_RATIO:
            continue
        scored.append({"word": word, "count": count, "ratio": round(ratio, 2)})

    scored.sort(key=lambda x: x["ratio"], reverse=True)
    return scored, len(texts)


def update_page(scored):
    html = PAGE_PATH.read_text(encoding="utf-8")
    new_data = json.dumps(scored, separators=(",", ":"))
    replacement = r"\g<1>const WORDS = " + new_data.replace("\\", "\\\\") + r";\g<2>"
    new_html, count = DATA_BLOCK_RE.subn(replacement, html)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one FAVORITE_WORDS_DATA block in {PAGE_PATH}, found {count}"
        )
    PAGE_PATH.write_text(new_html, encoding="utf-8")


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        sys.exit(f"CSV not found: {csv_path}")

    scored, review_count = compute_word_scores(csv_path)
    update_page(scored)

    print(f"Read {review_count} reviews from {csv_path}")
    print(f"Wrote {len(scored)} words to {PAGE_PATH}")
    print("Top 5:", ", ".join(w["word"] for w in scored[:5]))
    print("\nDon't forget to commit, push, and let GitHub Pages redeploy.")


if __name__ == "__main__":
    main()
