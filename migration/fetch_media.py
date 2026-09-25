#!/usr/bin/env python3
"""Download WP media originals via wsrv.nl into wp-content/uploads/."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
TSV = Path(__file__).resolve().parent / "urls_all.tsv"
UPLOADS = ROOT / "wp-content" / "uploads"
WESERV = "https://wsrv.nl/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})

EXTRA = [
    "https://prelom.bg/wp-content/uploads/2022/ukraine.pdf",
    "https://prelom.bg/wp-content/uploads/2017/05/prelom-logo-est.jpg",
]


def rel_of(url: str) -> str | None:
    path = unquote(urlparse(url).path)
    marker = "/wp-content/uploads/"
    if marker not in path:
        return None
    return path.split(marker, 1)[1].lstrip("/")


def download(src: str, dest: Path) -> tuple[int, str | None]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 200:
        return dest.stat().st_size, None
    ext = dest.suffix.lower()
    if ext in {".pdf", ".doc", ".docx"}:
        proxies = [
            src,
            "https://api.allorigins.win/raw?url=" + src,
            "https://corsproxy.io/?" + src,
        ]
        last = None
        for cand in proxies:
            try:
                r = SESSION.get(cand, timeout=90, stream=True)
                ctype = (r.headers.get("Content-Type") or "").lower()
                if r.status_code != 200 or "text/html" in ctype:
                    last = f"{r.status_code} {ctype}"
                    continue
                tmp = dest.with_suffix(dest.suffix + ".part")
                size = 0
                with tmp.open("wb") as fh:
                    for chunk in r.iter_content(65536):
                        if chunk:
                            fh.write(chunk)
                            size += len(chunk)
                if size < 200:
                    tmp.unlink(missing_ok=True)
                    last = "tiny"
                    continue
                tmp.replace(dest)
                return size, None
            except requests.RequestException as exc:
                last = str(exc)
        return 0, last
    params = {"url": src, "n": "-1"}
    if ext in {".jpg", ".jpeg"}:
        params.update({"output": "jpg", "q": "92"})
    elif ext == ".png":
        params["output"] = "png"
    try:
        r = SESSION.get(WESERV, params=params, timeout=90, stream=True)
        if r.status_code != 200:
            return 0, f"weserv {r.status_code}"
        tmp = dest.with_suffix(dest.suffix + ".part")
        size = 0
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(65536):
                if chunk:
                    fh.write(chunk)
                    size += len(chunk)
        if size < 64:
            tmp.unlink(missing_ok=True)
            return 0, "tiny"
        tmp.replace(dest)
        return size, None
    except requests.RequestException as exc:
        return 0, str(exc)


def main() -> int:
    urls = list(EXTRA)
    with TSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row["type"] == "media":
                urls.append(row["url"])
    ok = fail = 0
    total = 0
    for url in urls:
        rel = rel_of(url)
        if not rel:
            continue
        dest = UPLOADS / rel
        src = "https://prelom.bg/wp-content/uploads/" + rel
        size, err = download(src, dest)
        if err:
            fail += 1
            print(f"FAIL {rel} {err}", flush=True)
        else:
            ok += 1
            total += size
            print(f"ok {rel} {size}", flush=True)
    print(f"done ok={ok} fail={fail} bytes={total}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
