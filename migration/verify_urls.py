#!/usr/bin/env python3
"""Compare the WP inventory URLs with files produced by `jekyll build`."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
TSV = Path(__file__).resolve().parent / "urls_all.tsv"
REPORT = Path(__file__).resolve().parent / "url-verification.json"


def site_file_for(path: str) -> Path | None:
    path = unquote(path)
    if not path.startswith("/"):
        path = "/" + path
    if path == "/":
        candidates = [SITE / "index.html"]
    else:
        rel = path.strip("/")
        candidates = [
            SITE / rel / "index.html",
            SITE / f"{rel}.html",
            SITE / rel,
        ]
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def main() -> int:
    rows = []
    with TSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            url = (row.get("url") or "").strip()
            if url:
                rows.append(row)

    resolved = []
    missing = []
    for row in rows:
        url = row["url"].strip()
        kind = (row.get("type") or "").strip()
        parsed = urlparse(url)
        path = unquote(parsed.path) or "/"
        if kind != "media" and not path.endswith("/") and path != "/" and "." not in path.rsplit("/", 1)[-1]:
            path = path + "/"
        found = site_file_for(path)
        if found:
            resolved.append({"type": kind, "url": url, "path": path, "file": str(found.relative_to(ROOT))})
            continue
        reason = "not-built"
        if kind == "media":
            reason = "media-file-missing"
        elif kind == "tag":
            reason = "tag-archive-missing"
        elif kind == "category":
            reason = "category-archive-missing"
        elif kind == "author":
            reason = "author-archive-missing"
        missing.append({"type": kind, "url": url, "path": path, "reason": reason})

    report = {
        "inventory_urls": len(rows),
        "resolved": len(resolved),
        "unresolved": len(missing),
        "unresolved_by_reason": {},
        "unresolved_by_type": {},
        "missing": missing,
    }
    for item in missing:
        report["unresolved_by_reason"][item["reason"]] = report["unresolved_by_reason"].get(item["reason"], 0) + 1
        report["unresolved_by_type"][item["type"]] = report["unresolved_by_type"].get(item["type"], 0) + 1
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"urls={len(rows)} resolved={len(resolved)} unresolved={len(missing)}")
    for reason, count in sorted(report["unresolved_by_reason"].items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:4d}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
