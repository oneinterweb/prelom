#!/usr/bin/env python3
"""Scan _site for broken internal links and local image paths."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
REPORT = Path(__file__).resolve().parent / "link-check.json"
HREF_RE = re.compile(r"""(?:href|src)=["']([^"']+)["']""", re.I)


def exists(path: str) -> bool:
    path = unquote(path.split("#", 1)[0].split("?", 1)[0])
    if not path or path == "/":
        return (SITE / "index.html").exists()
    rel = path.lstrip("/")
    candidates = [
        SITE / rel,
        SITE / rel / "index.html",
        SITE / f"{rel}.html",
    ]
    return any(c.exists() for c in candidates)


def main() -> int:
    broken = []
    checked = 0
    for html in SITE.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        for match in HREF_RE.finditer(text):
            raw = match.group(1)
            if raw.startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "#")):
                continue
            checked += 1
            path = raw
            if not exists(path):
                broken.append({"page": str(html.relative_to(ROOT)), "href": raw})
    report = {"checked": checked, "broken": len(broken), "items": broken[:200]}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"checked={checked} broken={len(broken)}")
    for item in broken[:25]:
        print(f"  {item['page']} -> {item['href']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
