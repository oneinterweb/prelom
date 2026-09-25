#!/usr/bin/env python3
"""Download public prelom.bg pages via Jina reader into migration/raw/."""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parent
TSV = ROOT / "urls_all.tsv"
RAW = ROOT / "raw"
JINA = "https://r.jina.ai/"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "text/plain,*/*"})


def slug(url: str) -> str:
    path = unquote(urlparse(url).path or "/").strip("/")
    return path.split("/")[-1] if path else "home"


def safe(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-._" or "\u0400" <= ch <= "\u04FF" else "-" for ch in name)[:160]


def fetch(url: str) -> str:
    for attempt in range(8):
        r = SESSION.get(JINA + url, timeout=45)
        if r.status_code in (403, 429):
            wait = 50
            print(f"  {r.status_code} {url} sleep {wait}s", flush=True)
            time.sleep(wait)
            continue
        if r.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        if len(r.text) < 80:
            time.sleep(4)
            continue
        return r.text
    raise RuntimeError(f"failed {url}")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    with TSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row["type"] in {"post", "page", "category", "author"}:
                rows.append(row)
    extra = []
    for row in rows:
        if row["type"] == "category":
            extra.append({**row, "url": row["url"].rstrip("/") + "/page/2/", "page_n": 2})
            extra.append({**row, "url": row["url"].rstrip("/") + "/page/3/", "page_n": 3})
    ok = 0
    for row in rows + extra:
        url = row["url"]
        kind = row["type"]
        ident = row.get("id") or "-"
        s = slug(url)
        if kind == "category" and row.get("page_n"):
            name = f"cat-{safe(s)}-p{row['page_n']}.md"
        elif kind == "category":
            name = f"cat-{safe(s)}.md"
        elif kind == "author":
            name = f"author-{safe(s)}.md"
        elif kind == "post":
            name = f"post-{ident}-{safe(s)}.md"
        else:
            name = "page-home.md" if s in {"", "home"} or url.rstrip("/") == "https://prelom.bg" else f"page-{ident}-{safe(s)}.md"
        dest = RAW / name
        if dest.exists() and dest.stat().st_size > 80:
            print(f"skip {name}", flush=True)
            ok += 1
            continue
        try:
            text = fetch(url)
        except Exception as exc:
            print(f"FAIL {url}: {exc}", flush=True)
            continue
        dest.write_text(text, encoding="utf-8")
        ok += 1
        print(f"ok {name} {len(text)}", flush=True)
        time.sleep(4.2)
    print(f"done cached={ok}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
