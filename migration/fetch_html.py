#!/usr/bin/env python3
"""Download public prelom.bg HTML via allorigins (Cloudflare bypass) into migration/raw/html/."""

from __future__ import annotations

import csv
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parent
TSV = ROOT / "urls_all.tsv"
OUT = ROOT / "raw" / "html"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "text/html,*/*"})


def slug(url: str) -> str:
    path = unquote(urlparse(url).path or "/").strip("/")
    return path.split("/")[-1] if path else "home"


def safe(name: str) -> str:
    return "".join(
        ch if ch.isalnum() or ch in "-._" or "\u0400" <= ch <= "\u04FF" else "-"
        for ch in name
    )[:160]


def dest_name(row: dict) -> str:
    kind = row["type"]
    ident = row.get("id") or "-"
    s = slug(row["url"])
    if kind == "category":
        extra = f"-p{row['page_n']}" if row.get("page_n") else ""
        return f"cat-{safe(s)}{extra}.html"
    if kind == "author":
        return f"author-{safe(s)}.html"
    if kind == "post":
        return f"post-{ident}-{safe(s)}.html"
    if s in {"", "home"} or row["url"].rstrip("/") == "https://prelom.bg":
        return "page-home.html"
    return f"page-{ident}-{safe(s)}.html"


def fetch(url: str) -> str:
    proxies = [
        "https://api.allorigins.win/raw?url=" + quote(url, safe=""),
        "https://api.allorigins.win/raw?url=" + quote(url, safe="") + "&t=" + str(int(time.time())),
    ]
    last = None
    for attempt, candidate in enumerate(proxies * 3):
        try:
            r = SESSION.get(candidate, timeout=60)
            if r.status_code in (403, 429, 502, 503, 520, 522):
                last = f"{r.status_code}"
                time.sleep(8 + attempt * 4)
                continue
            if r.status_code != 200 or len(r.text) < 800:
                last = f"{r.status_code} len={len(r.text)}"
                time.sleep(3)
                continue
            if "entry-content" not in r.text and "entry-title" not in r.text and "class=\"post\"" not in r.text:
                # category archives use different markup
                if "posted-on" not in r.text.lower() and "category" not in url:
                    last = "no-entry-content"
                    time.sleep(2)
                    continue
            return r.text
        except requests.RequestException as exc:
            last = str(exc)
            time.sleep(4)
    raise RuntimeError(last or "fetch failed")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
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
    ok = fail = skip = 0
    for row in rows + extra:
        name = dest_name(row)
        dest = OUT / name
        if dest.exists() and dest.stat().st_size > 800:
            print(f"skip {name}", flush=True)
            skip += 1
            continue
        try:
            text = fetch(row["url"])
        except Exception as exc:
            print(f"FAIL {row['url']}: {exc}", flush=True)
            fail += 1
            time.sleep(4)
            continue
        dest.write_text(text, encoding="utf-8")
        ok += 1
        print(f"ok {name} {len(text)}", flush=True)
        time.sleep(1.6)
    print(f"done ok={ok} skip={skip} fail={fail}", flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
