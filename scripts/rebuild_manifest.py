#!/usr/bin/env python3
"""
Rebuild web/manifest.json from disk.

Scans web/<Category>/<YYYY-MM-DD>/data.json and generates a fresh manifest
with categories sorted by their preferred label. This runs as a post-step in
the daily pipeline, after all parallel builders finish — which sidesteps the
race that would otherwise exist if each builder tried to update the manifest
independently.

Usage:
  python3 scripts/rebuild_manifest.py
  python3 scripts/rebuild_manifest.py --project-root /path/to/repo
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Ordered: this is the order tabs will appear in the UI.
CATEGORY_LABELS = {
    "AI": "AI 科技",
    "GitHub": "GitHub 趋势",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def rebuild(project_root: Path) -> dict:
    web_root = project_root / "web"
    if not web_root.is_dir():
        raise SystemExit(f"no web/ directory at {web_root}")

    categories: dict[str, dict] = {}
    for category_dir in sorted(web_root.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        # Skip non-category subdirs like css, js, fonts, shared/
        if category in {"css", "js", "fonts"} or category.startswith("."):
            continue

        dates = []
        for date_dir in category_dir.iterdir():
            if not date_dir.is_dir():
                continue
            if not DATE_RE.match(date_dir.name):
                continue
            if (date_dir / "data.json").is_file():
                dates.append(date_dir.name)

        if not dates:
            continue

        dates.sort(reverse=True)  # newest first
        categories[category] = {
            "label": CATEGORY_LABELS.get(category, category),
            "dates": dates,
        }

    # Preserve the CATEGORY_LABELS ordering so tabs render in a predictable order;
    # unknown categories go at the end in alphabetical order.
    known = [k for k in CATEGORY_LABELS if k in categories]
    unknown = sorted(k for k in categories if k not in CATEGORY_LABELS)
    ordered = {k: categories[k] for k in known + unknown}

    manifest = {"categories": ordered}
    manifest_path = web_root / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"wrote {manifest_path}")
    for k, v in ordered.items():
        print(f"  {k}: {len(v['dates'])} dates (latest: {v['dates'][0]})")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", default=None)
    args = ap.parse_args()
    project_root = (
        Path(args.project_root).resolve()
        if args.project_root
        else Path(__file__).resolve().parents[1]
    )
    rebuild(project_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
