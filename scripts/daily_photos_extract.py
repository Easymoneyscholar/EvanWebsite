#!/usr/bin/env python3
"""
Phase 1 of 3 for the "daily photo memories" homepage background.

Reads your local Apple Photos library, groups photos by calendar day
(month + day, ignoring year), and exports resized candidates for each
day into a local staging folder for review. Does NOT touch the git
repo or publish anything.

Usage:
    python3 scripts/daily_photos_extract.py

Requires:
    pip3 install osxphotos
    Terminal (or your IDE) needs Photos access - macOS will prompt the
    first time this runs.

Next step after this: open the review tool (phase 2) to pick/exclude
photos, then run daily_photos_finalize.py (phase 3).
"""
import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import osxphotos

STAGING_DIR = Path.home() / "Desktop" / "daily-photos-staging"
MAX_CANDIDATES_PER_DAY = 6
MAX_DIMENSION = 1200  # resized longest edge, plenty for a review thumbnail and a hero bg

PREFERRED_LABELS = {
    "Outdoor", "Land", "Sky", "Water Body", "Water", "Mountain", "Beach",
    "Landscape", "Nature", "Coast", "Field", "Forest", "Sunset", "Sunrise",
    "Snow", "Lake", "River", "Cloudy", "Cloud",
}
DEPRIORITIZED_LABELS = {"Document", "Handwriting", "Receipt", "Screenshot"}


def place_string(photo):
    if not photo.place or not photo.place.address:
        return None
    addr = photo.place.address
    parts = [p for p in (addr.city, addr.state_province, addr.country) if p]
    return ", ".join(parts) if parts else None


def score_photo(photo):
    score = 0
    if photo.width and photo.height and photo.width > photo.height:
        score += 2
    if photo.location and photo.location[0] is not None:
        score += 2
    labels = set(photo.labels or [])
    if labels & PREFERRED_LABELS:
        score += 2
    if labels & DEPRIORITIZED_LABELS:
        score -= 3
    if "People" in labels:
        score -= 2
    if photo.favorite:
        score += 1
    return score


def main():
    STAGING_DIR.mkdir(exist_ok=True)
    (STAGING_DIR / "images").mkdir(exist_ok=True)

    print("Loading Photos library (this can take a minute)...")
    db = osxphotos.PhotosDB()
    photos = db.photos(images=True, movies=False)
    print(f"Found {len(photos)} total photos")

    by_day = defaultdict(list)
    for p in photos:
        if p.hidden or p.intrash or not p.date:
            continue
        day_key = f"{p.date.month:02d}-{p.date.day:02d}"
        by_day[day_key].append(p)

    print(f"Spans {len(by_day)} distinct calendar days")

    manifest = {}
    exported_count = 0
    for day_key, day_photos in sorted(by_day.items()):
        scored = sorted(day_photos, key=score_photo, reverse=True)
        chosen = scored[:MAX_CANDIDATES_PER_DAY]

        candidates = []
        for i, photo in enumerate(chosen):
            out_name = f"{day_key}_{i}.jpg"
            out_path = STAGING_DIR / "images" / out_name

            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    exported = photo.export(tmpdir, "original")
                except Exception as e:
                    print(f"  skip {photo.original_filename} ({day_key}): export failed: {e}")
                    continue
                if not exported:
                    continue

                result = subprocess.run(
                    [
                        "sips", "-s", "format", "jpeg",
                        "-Z", str(MAX_DIMENSION),
                        exported[0],
                        "--out", str(out_path),
                    ],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    print(f"  skip {photo.original_filename} ({day_key}): sips failed: {result.stderr.strip()}")
                    continue

            candidates.append(
                {
                    "file": out_name,
                    "year": photo.date.year,
                    "location": place_string(photo),
                    "score": score_photo(photo),
                }
            )
            exported_count += 1

        if candidates:
            manifest[day_key] = candidates

    manifest_path = STAGING_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\nExported {exported_count} candidate images across {len(manifest)} days")
    print(f"Staging folder: {STAGING_DIR}")
    print("\nNext: run the review tool to pick/exclude photos per day.")


if __name__ == "__main__":
    main()
