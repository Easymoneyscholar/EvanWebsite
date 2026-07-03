#!/usr/bin/env python3
"""
Phase 3 of 3 for the "daily photo memories" homepage background.

Reads your decisions from the review tool (phase 2) and copies only the
approved, chosen photo per day into the site's assets folder, building
the public manifest (day -> location/year, no coordinates).

Usage:
    python3 scripts/daily_photos_finalize.py [path/to/decisions.json]

Defaults to ~/Desktop/daily-photos-staging/decisions.json (wherever the
review tool's "Download decisions.json" button saved it - move it into
the staging folder first if it landed in ~/Downloads).
"""
import json
import shutil
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = Path.home() / "Desktop" / "daily-photos-staging"
DEFAULT_DECISIONS = STAGING_DIR / "decisions.json"
OUT_DIR = SITE_ROOT / "assets" / "daily-photos"


def main():
    decisions_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DECISIONS
    if not decisions_path.exists():
        sys.exit(
            f"decisions.json not found at {decisions_path}\n"
            "Download it from the review tool first (button in the top bar), "
            "then move it into the staging folder or pass its path as an argument."
        )

    manifest_path = STAGING_DIR / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"staging manifest not found at {manifest_path} - run daily_photos_extract.py first")

    decisions = json.loads(decisions_path.read_text())
    staging_manifest = json.loads(manifest_path.read_text())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # clear any previously finalized images so removed/re-excluded days don't linger
    for f in OUT_DIR.glob("*.jpg"):
        f.unlink()

    public_manifest = {}
    included = 0
    excluded = 0
    for day_key, decision in decisions.items():
        if decision.get("excluded"):
            excluded += 1
            continue
        candidates = staging_manifest.get(day_key)
        if not candidates:
            continue
        candidate = candidates[decision["index"]]

        src = STAGING_DIR / "images" / candidate["file"]
        dst = OUT_DIR / f"{day_key}.jpg"
        shutil.copyfile(src, dst)

        public_manifest[day_key] = {
            "year": candidate["year"],
            "location": candidate["location"],
        }
        included += 1

    (OUT_DIR / "manifest.json").write_text(json.dumps(public_manifest, indent=2))

    print(f"Included {included} days, excluded {excluded}")
    print(f"Wrote images + manifest.json to {OUT_DIR}")
    print("\nNext: commit assets/daily-photos/, push, and verify the homepage.")


if __name__ == "__main__":
    main()
