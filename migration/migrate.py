#!/usr/bin/env python3
"""Migrate public prelom.bg WordPress content into this Jekyll site.

The WP REST API, xmlrpc and wp-login are blocked by WP Cerber, and the
origin is behind a Cloudflare challenge for datacenter IPs. This script
reads public HTML via the Jina reader (https://r.jina.ai/) and downloads
media through images.weserv.nl. Re-run after a successful scrape with
`--from-cache` to rebuild Markdown without hitting the network.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as html_to_md

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path(__file__).resolve().parent / "raw"
POSTS_DIR = ROOT / "_posts"
PAGES_DIR = ROOT / "_pages"
TAX_DIR = ROOT / "_pages" / "tax"
UPLOADS_DIR = ROOT / "wp-content" / "uploads"
IMAGES_DIR = ROOT / "assets" / "images"
TSV = Path(__file__).resolve().parent / "urls_all.tsv"
REPORT_FILE = Path(__file__).resolve().parent / "report.json"
MEDIA_MANIFEST = Path(__file__).resolve().parent / "media-manifest.json"

SITE = "https://prelom.bg"
JINA = "https://r.jina.ai/"
WESERV = "https://wsrv.nl/"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": BROWSER_UA,
        "Accept": "text/plain,text/html,*/*;q=0.8",
        "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
    }
)

DEAD_SHORTCODES = [
    re.compile(r"\[pta_member_directory[^\]]*\]", re.I),
    re.compile(r"\[pta_sign_up_sheet[^\]]*\]", re.I),
    re.compile(r"\[pta_member_contact[^\]]*\]", re.I),
    re.compile(r"\[mc4wp_form[^\]]*\]", re.I),
    re.compile(r"\[contact-form[^\]]*\].*?\[/contact-form\]", re.I | re.S),
    re.compile(r"\[contact-form[^\]]*\]", re.I),
    re.compile(r"\[/?contact-field[^\]]*\]", re.I),
]
DEAD_SCRIPT_RE = re.compile(
    r'<script[^>]+src=["\'][^"\']*prelom\.bg/news/form/generate\.js[^"\']*["\'][^>]*>\s*</script>',
    re.I,
)
DEALAI_RE = re.compile(r"https?://(?:api\.marketing\.)?deal\.ai[^\s\"'<>]*", re.I)
WP_COMMENT_RE = re.compile(r"<!--\s*/?wp:.*?-->", re.S)
THUMB_RE = re.compile(r"-(\d+)x(\d+)(?=\.[A-Za-z0-9]+$)")
JINA_META_RE = re.compile(
    r"^Title:\s*(?P<title>.+?)\s*$"
    r"(?:^URL Source:\s*(?P<url>.+?)\s*$)?"
    r"(?:^Published Time:\s*(?P<date>.+?)\s*$)?"
    r"(?:^Markdown Content:\s*$)?",
    re.M,
)
CHROME_MARKERS = (
    "Търсене за:",
    "## Последни публикации",
    "### Вашият коментар",
    "Вашият коментар Отказ",
    "Трябва да влезете, за да публикувате коментар",
)
CERBER_RE = re.compile(
    r"\*\*Notice\*\*:.*?functions\.php\*\* on line \*\*\d+\*\*",
    re.S,
)
CERBER_HTML_RE = re.compile(
    r"<b>Notice</b>:.+?functions\.php</b> on line <b>\d+</b><br\s*/?>",
    re.S | re.I,
)

CONTACT_SLUGS = {"contact"}
REDIRECT_IF_EMPTY = {
    "volunteers",
    "contact-volunteer",
    "събития",
}
KEEP_PAGES_WITH_EMBEDS = {
    "donate": "{% include paypal-donate.html %}\n",
    "newsletter": "{% include mailchimp-form.html %}\n",
    "contact": "{% include contact-form.html %}\n",
}

CATEGORY_NAMES = {
    "pouchenie": "Поучение",
    "obshti": "Общи",
    "apostolski": "Апостолски",
    "positions": "Позиции",
    "english": "English",
    "prorocheski": "Пророчески",
    "videochat": "Видео",
    "архив": "Архив",
    "archives": "Archives",
    "дейности": "Дейности",
}

AUTHOR_SLUG_FROM_NAME = {
    "админ": "admin",
    "admin": "admin",
    "поликсения": "admin3",
    "admin3": "admin3",
    "георги бакалов": "admin",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fm_quote(value: str) -> str:
    return yaml.safe_dump(value, allow_unicode=True, default_style='"').strip()


def write_front_matter(data: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in data.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {fm_quote(str(item)) if isinstance(item, str) else item}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            dumped = yaml.safe_dump(value, allow_unicode=True, default_flow_style=False).strip()
            for row in dumped.splitlines():
                lines.append(f"  {row}")
        else:
            lines.append(f"{key}: {fm_quote(str(value))}")
    lines.append("---")
    lines.append("")
    body = body.lstrip("\n")
    if not body.endswith("\n"):
        body += "\n"
    return "\n".join(lines) + body


def safe_filename(slug: str, fallback: str) -> str:
    slug = slug.strip().replace("/", "-")
    slug = re.sub(r"[^\w\-.\u0400-\u04FF]+", "-", slug, flags=re.UNICODE)
    slug = slug.strip("-.") or fallback
    return slug[:180]


def decode_slug(path: str) -> str:
    return unquote(path).strip("/")


def load_inventory() -> list[dict[str, str]]:
    rows = []
    with TSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("url"):
                rows.append(row)
    return rows


def path_of(url: str) -> str:
    return unquote(urlparse(url).path or "/")


def slug_of(url: str) -> str:
    path = path_of(url).strip("/")
    return path.split("/")[-1] if path else ""


def jina_get(url: str, retries: int = 8) -> str:
    """Fetch a URL through the Jina reader (markdown)."""
    target = JINA + url
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = SESSION.get(target, timeout=45)
            if r.status_code in (403, 429, 502, 503, 504):
                wait = 45 if r.status_code in (403, 429) else 8 * (attempt + 1)
                log(f"  jina {r.status_code} {url} — sleep {wait}s")
                time.sleep(wait)
                last_err = RuntimeError(f"{r.status_code}")
                continue
            r.raise_for_status()
            text = r.text or ""
            if text.strip() in {"", "<br><head></head><body></body></br>"}:
                last_err = RuntimeError("empty jina body")
                time.sleep(4.0 * (attempt + 1))
                continue
            return text
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(3.0 * (attempt + 1))
    raise RuntimeError(f"Jina GET failed {url}: {last_err}")


def parse_jina_markdown(raw: str) -> dict[str, str]:
    title = ""
    url = ""
    date = ""
    body = raw
    m_title = re.search(r"^Title:\s*(.+)$", raw, re.M)
    if m_title:
        title = m_title.group(1).strip()
        title = re.sub(r"\s*[–—|-]\s*Християнски Център Прелом.*$", "", title).strip()
    m_url = re.search(r"^URL Source:\s*(.+)$", raw, re.M)
    if m_url:
        url = m_url.group(1).strip()
    m_date = re.search(r"^Published Time:\s*(.+)$", raw, re.M)
    if m_date:
        date = m_date.group(1).strip()
    marker = "Markdown Content:"
    if marker in raw:
        body = raw.split(marker, 1)[1]
    body = CERBER_RE.sub("", body)
    body = re.sub(
        r"Notice: Function _load_textdomain_just_in_time.*?(?:\n|$)",
        "",
        body,
    )
    # Drop chrome before the article (nav) and after comments / sidebar
    lines = body.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("# ") and "Християнски Център Прелом" not in line:
            start = i
            break
        if line.startswith("Skip to content") or line.startswith("[Skip to content]"):
            start = i + 1
    lines = lines[start:]
    cut = len(lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(marker) or marker in stripped for marker in CHROME_MARKERS):
            cut = i
            break
    body = "\n".join(lines[:cut]).strip()
    # Drop leftover top nav list that sometimes survives
    body = re.sub(
        r"^(\s*\*\s*\[(?:Начало|Поучения|YouTube|Facebook|X)\][^\n]*\n)+",
        "",
        body,
    )
    body = re.sub(r"^\[Християнски Център Прелом\]\([^)]+\)\s*", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return {"title": title, "url": url, "date": date, "body": body}


def strip_dead_markup(text: str) -> str:
    for pat in DEAD_SHORTCODES:
        text = pat.sub("", text)
    text = DEAD_SCRIPT_RE.sub("", text)
    text = DEALAI_RE.sub("", text)
    text = re.sub(r"https?://prelom\.bg/news/form/generate\.js\?id=\d+", "", text)
    return text


def protect_embeds(html: str) -> tuple[str, dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    placeholders: dict[str, str] = {}
    idx = 0
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src") or ""
        if "deal.ai" in src:
            iframe.decompose()
            continue
        title = iframe.get("title") or "embed"
        wrapper = (
            f'<div class="responsive-embed">'
            f'<iframe src="{src}" title="{title}" allowfullscreen loading="lazy"></iframe>'
            f"</div>"
        )
        key = f"EMBEDPLACEHOLDER{idx}XYZ"
        placeholders[key] = wrapper
        iframe.replace_with(NavigableString(key))
        idx += 1
    for script in soup.find_all("script"):
        src = script.get("src") or ""
        if "threefold.life/crm/form/generate.js" in src:
            key = f"EMBEDPLACEHOLDER{idx}XYZ"
            placeholders[key] = '{% include threefold-form.html %}'
            script.replace_with(NavigableString(key))
            idx += 1
        elif "deal.ai" in src:
            script.decompose()
    return str(soup), placeholders


def rewrite_site_href(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in {"yszctuqddd.wpdns.site", "yszctuqddd-staging.wpdns.site"}:
        return "@@BASEURL@@/"
    if host not in {"prelom.bg", ""} and "wp-content/uploads" not in (parsed.path or ""):
        return None
    path = unquote(parsed.path or "/")
    if "/wp-content/uploads/" in path:
        rel = path.split("/wp-content/uploads/", 1)[1]
        rel = THUMB_RE.sub("", rel)
        return "@@BASEURL@@/wp-content/uploads/" + rel.lstrip("/")
    if "/wp-content/" in path or "/wp-json/" in path or "/wp-admin/" in path:
        return None
    parts = [p for p in path.split("/") if p]
    new_path = "/" + "/".join(parts)
    last = parts[-1] if parts else ""
    if new_path != "/" and not new_path.endswith("/") and "." not in last:
        new_path = new_path.rstrip("/") + "/"
    if new_path in {"//", ""}:
        new_path = "/"
    return "@@BASEURL@@" + new_path


def rewrite_html_urls(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["a", "img", "source", "audio", "video"]):
        for attr in ("href", "src"):
            val = tag.get(attr)
            if not val:
                continue
            rewritten = rewrite_site_href(val)
            if rewritten:
                tag[attr] = rewritten
        if tag.has_attr("srcset"):
            del tag["srcset"]
        for attr in ("data-srcset", "sizes", "data-src"):
            if tag.has_attr(attr):
                if attr == "data-src" and not tag.get("src"):
                    rewritten = rewrite_site_href(tag[attr])
                    if rewritten:
                        tag["src"] = rewritten
                del tag[attr]
    return str(soup)


def html_to_markdown(html: str) -> str:
    html = CERBER_HTML_RE.sub("", html or "")
    html = WP_COMMENT_RE.sub("", html)
    html = strip_dead_markup(html)
    html = rewrite_html_urls(html)
    html, embeds = protect_embeds(html)
    md = html_to_md(
        html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
        escape_underscores=False,
        escape_asterisks=False,
    )
    # Escape leftover Liquid in imported WP text before we inject our own tags.
    md = md.replace("{{", "{{ '{{' }}").replace("{%", "{{ '{%' }}")
    for key, embed in embeds.items():
        md = md.replace(key, "\n\n" + embed + "\n\n")
    md = md.replace("@@BASEURL@@", "{{ site.baseurl }}")
    md = md.replace("@@CONTACT_FORM@@", "{% include contact-form.html %}")
    md = md.replace("@@MAILCHIMP@@", "{% include mailchimp-form.html %}")
    md = md.replace("@@PAYPAL@@", "{% include paypal-donate.html %}")
    md = md.replace("@@THREEFOLD@@", "{% include threefold-form.html %}")
    md = convert_youtube_links(md)
    md = re.sub(r"iFrameResize\([^;]*\);?", "", md)
    md = re.sub(r"\(function\s*\(\)\s*\{.*?\}\)\s*\(\)", "", md, flags=re.S)
    md = re.sub(
        r"if\s*\(navigator\.userAgent\.match\([^;]+;",
        "",
        md,
    )
    md = re.sub(r"sf\[sf\.length[^\n]*", "", md)
    md = re.sub(r"^Add your Typeform title here\s*", "", md, flags=re.M)
    md = re.sub(r"html\{\s*margin:\s*0;[^}]+\}(?:\s*iframe\{[^}]+\})?", "", md)
    md = md.replace("/аudio/", "/audio/")
    md = md.replace("]({{ site.baseurl }}/wp-admin/post.php)", "]({{ site.baseurl }}/ден-15-семейство-от-семейства/)")
    md = re.sub(r"^#\s*$", "", md, flags=re.M)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md


YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|playlist\?list=)|youtu\.be/)([A-Za-z0-9_-]{6,})"
)


def youtube_iframe(url: str) -> str | None:
    m = YOUTUBE_ID_RE.search(url)
    if not m:
        return None
    token = m.group(1)
    if "playlist" in url or token.startswith("PL"):
        src = f"https://www.youtube.com/embed/videoseries?list={token}"
    else:
        src = f"https://www.youtube.com/embed/{token}"
    return (
        '<div class="responsive-embed">'
        f'<iframe src="{src}" title="YouTube" allowfullscreen loading="lazy"></iframe>'
        "</div>"
    )


def convert_youtube_links(md: str) -> str:
    def repl(match: re.Match) -> str:
        return youtube_iframe(match.group(1)) or match.group(0)

    md = re.sub(
        r"\[(?:youtube|embed)(?:\s+|\]\()?(https?://[^\s\]\)]+)(?:\)|\])?",
        repl,
        md,
        flags=re.I,
    )
    return md


def rewrite_markdown_urls(md: str) -> str:
    def link_repl(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        rewritten = rewrite_site_href(url)
        if rewritten:
            rewritten = rewritten.replace("@@BASEURL@@", "{{ site.baseurl }}")
            return f"[{label}]({rewritten})"
        return match.group(0)

    md = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", link_repl, md)
    md = re.sub(
        r"!\[([^\]]*)\]\((https?://[^)]+)\)",
        lambda m: (
            f"![{m.group(1)}]({rewrite_site_href(m.group(2)).replace('@@BASEURL@@', '{{ site.baseurl }}')})"
            if rewrite_site_href(m.group(2))
            else m.group(0)
        ),
        md,
    )
    md = md.replace("https://yszctuqddd.wpdns.site/", "{{ site.baseurl }}/")
    md = md.replace("https://yszctuqddd.wpdns.site", "{{ site.baseurl }}/")
    return md


def meaningful_text(md: str) -> str:
    text = re.sub(r"{%.*?%}", "", md, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[#*_`>-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def collect_media_from_text(text: str) -> set[str]:
    urls: set[str] = set()
    for match in re.findall(r"https?://[^\s\"'<>\)]+wp-content/uploads/[^\s\"'<>\)]+", text or ""):
        urls.add(match.rstrip(").,;"))
    return urls


def original_rel(url: str) -> str | None:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    marker = "/wp-content/uploads/"
    if marker not in path:
        return None
    rel = path.split(marker, 1)[1]
    return rel.lstrip("/")


def download_via_weserv(src_url: str, dest: Path) -> tuple[int, str | None]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 200:
        return dest.stat().st_size, None
    ext = dest.suffix.lower()
    params = {"url": src_url, "n": "-1"}
    if ext in {".jpg", ".jpeg"}:
        params["output"] = "jpg"
        params["q"] = "92"
    elif ext == ".png":
        params["output"] = "png"
    elif ext == ".webp":
        params["output"] = "webp"
    try:
        r = SESSION.get(WESERV, params=params, timeout=90, stream=True)
        if r.status_code != 200:
            return 0, f"weserv {r.status_code}"
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in ctype or "text/plain" in ctype:
            return 0, f"weserv not image {ctype}"
        tmp = dest.with_suffix(dest.suffix + ".part")
        size = 0
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(64 * 1024):
                if chunk:
                    fh.write(chunk)
                    size += len(chunk)
        if size < 64:
            tmp.unlink(missing_ok=True)
            return 0, "tiny body"
        tmp.replace(dest)
        return size, None
    except requests.RequestException as exc:
        return 0, str(exc)


def download_binary_fallback(src_url: str, dest: Path) -> tuple[int, str | None]:
    """Try a few public proxies for PDF/DOC that weserv cannot convert."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 200:
        return dest.stat().st_size, None
    proxies = [
        src_url,
        "https://api.allorigins.win/raw?url=" + quote(src_url, safe=""),
        "https://corsproxy.io/?" + src_url,
    ]
    last = None
    for candidate in proxies:
        try:
            r = SESSION.get(candidate, timeout=90, stream=True, allow_redirects=True)
            ctype = (r.headers.get("Content-Type") or "").lower()
            if r.status_code != 200 or "text/html" in ctype:
                last = f"{r.status_code} {ctype} {candidate}"
                continue
            tmp = dest.with_suffix(dest.suffix + ".part")
            size = 0
            with tmp.open("wb") as fh:
                for chunk in r.iter_content(64 * 1024):
                    if chunk:
                        fh.write(chunk)
                        size += len(chunk)
            if size < 200:
                tmp.unlink(missing_ok=True)
                last = f"tiny {candidate}"
                continue
            tmp.replace(dest)
            return size, None
        except requests.RequestException as exc:
            last = str(exc)
    return 0, last


def author_slug(name: str | None) -> str:
    if not name:
        return "admin"
    return AUTHOR_SLUG_FROM_NAME.get(name.strip().lower(), "admin")


def extract_author_from_text(text: str) -> str:
    m = re.search(r"Posted on .+? by\s+([^\n]+)", text)
    if m:
        name = m.group(1).strip()
        if name:
            return author_slug(name)
    m = re.search(r"\bby (Админ|Поликсения|admin3?)\b", text)
    if m:
        return author_slug(m.group(1))
    return "admin"


def fetch_cached(name: str, url: str, refresh: bool) -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.md"
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    text = jina_get(url)
    path.write_text(text, encoding="utf-8")
    time.sleep(3.3)
    return text


def parse_category_listing(raw: str) -> list[dict[str, str]]:
    """Best-effort extraction of items listed on a WP category archive."""
    items = []
    parsed = parse_jina_markdown(raw)
    body = parsed["body"]
    for match in re.finditer(
        r"##\s+\[([^\]]+)\]\((https://prelom\.bg/[^)]+)\)",
        body,
    ):
        title = match.group(1).strip()
        slug = slug_of(match.group(2))
        items.append({"title": title, "slug": slug, "date": "", "author": ""})
    if not items:
        blocks = re.split(r"\n(?=## )", body)
        for block in blocks:
            title_m = re.search(r"^##\s+(.+)$", block, re.M)
            if not title_m:
                continue
            title = re.sub(r"^\[([^\]]+)\]\([^)]+\)", r"\1", title_m.group(1)).strip()
            posted = re.search(r"Posted on\s+(\d{1,2}/\d{1,2}/\d{4}).*?by\s*([^\n]*)", block)
            date = ""
            author = "admin"
            if posted:
                d, a = posted.group(1), posted.group(2).strip()
                try:
                    day, month, year = d.split("/")
                    date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except ValueError:
                    date = ""
                author = author_slug(a) if a else "admin"
            items.append({"title": title, "slug": "", "date": date, "author": author})
    # Posted-on metadata, if present, is applied to the previous item
    posted_all = re.findall(
        r"Posted on\s+(\d{1,2}/\d{1,2}/\d{4}).*?by\s*([^\n]*)",
        body,
    )
    for item, posted in zip(items, posted_all):
        d, a = posted
        try:
            day, month, year = d.split("/")
            item["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except ValueError:
            pass
        if a.strip():
            item["author"] = author_slug(a)
    return items


def apply_special_page(slug: str, body: str) -> str:
    body = strip_dead_markup(body)
    if slug == "donate" and "paypal-donate.html" not in body:
        body = (body.strip() + "\n\n{% include paypal-donate.html %}\n") if body.strip() else KEEP_PAGES_WITH_EMBEDS["donate"]
    if slug == "newsletter" and "mailchimp-form.html" not in body:
        body = KEEP_PAGES_WITH_EMBEDS["newsletter"]
    if slug == "contact" and "contact-form.html" not in body:
        body = KEEP_PAGES_WITH_EMBEDS["contact"]
    if slug == "ukraine":
        pdf = "{{ site.baseurl }}/wp-content/uploads/2022/ukraine.pdf"
        if "ukraine.pdf" not in body:
            body = (
                (body.strip() + "\n\n" if body.strip() else "")
                + f"[Изтеглете документа (PDF)]({pdf})\n"
            )
    return body


def write_tax_page(kind: str, slug: str, title: str) -> Path:
    TAX_DIR.mkdir(parents=True, exist_ok=True)
    if kind == "category":
        permalink = f"/category/{slug}/"
        prefix = "category"
    elif kind == "tag":
        permalink = f"/tag/{slug}/"
        prefix = "tag"
    else:
        permalink = f"/author/{slug}/"
        prefix = "author"
    fname = f"{prefix}-{safe_filename(slug, slug)}.md"
    path = TAX_DIR / fname
    fm = {
        "title": title,
        "permalink": permalink,
        "layout": "archive-taxonomy",
        "taxonomy_type": kind,
        "taxonomy": slug,
        "author_profile": False,
        "share": False,
        "comments": False,
    }
    path.write_text(write_front_matter(fm, ""), encoding="utf-8")
    return path


def reset_generated() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    TAX_DIR.mkdir(parents=True, exist_ok=True)
    keep_pages = {"search.md", "year-archive.md", "thanks.md"}
    for path in POSTS_DIR.glob("*.md"):
        path.unlink()
    for path in PAGES_DIR.glob("*.md"):
        if path.name not in keep_pages:
            path.unlink()
    for path in TAX_DIR.glob("*.md"):
        path.unlink()


def homepage_from_saved_html() -> str:
    """Use the already-captured homepage HTML when present."""
    cached = [
        Path("/tmp/prelom-probe/jina-home.html"),
        RAW_DIR / "page-home.html",
    ]
    for path in cached:
        if path.exists() and path.stat().st_size > 1000:
            html = path.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(html, "lxml")
            ec = soup.select_one(".entry-content")
            if ec:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                (RAW_DIR / "page-home.html").write_text(str(ec), encoding="utf-8")
                return html_to_markdown(str(ec))
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Re-download Jina captures")
    parser.add_argument("--from-cache", action="store_true", help="Use migration/raw only")
    parser.add_argument("--from-html", action="store_true", help="Convert migration/raw/html only")
    parser.add_argument("--skip-media", action="store_true")
    parser.add_argument("--skip-tags-fetch", action="store_true", help="Do not fetch tag archives")
    args = parser.parse_args()
    html_cache = RAW_DIR / "html"
    if args.from_html or (
        args.from_cache and html_cache.exists() and any(html_cache.glob("post-*.html"))
    ):
        from convert_html import main as convert_main

        return convert_main()
    refresh = args.refresh and not args.from_cache

    inventory = load_inventory()
    posts_inv = [r for r in inventory if r["type"] == "post"]
    pages_inv = [r for r in inventory if r["type"] == "page"]
    cats_inv = [r for r in inventory if r["type"] == "category"]
    tags_inv = [r for r in inventory if r["type"] == "tag"]
    authors_inv = [r for r in inventory if r["type"] == "author"]
    media_inv = [r for r in inventory if r["type"] == "media"]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    reset_generated()

    title_index: dict[str, dict[str, Any]] = {}
    cat_map: dict[str, set[str]] = {}
    author_map: dict[str, str] = {}
    date_map: dict[str, str] = {}

    log("Fetching category archives…")
    for row in cats_inv:
        slug = slug_of(row["url"])
        name = f"cat-{safe_filename(slug, slug)}"
        try:
            raw = fetch_cached(name, row["url"], refresh)
        except Exception as exc:
            log(f"  category fail {slug}: {exc}")
            continue
        items = parse_category_listing(raw)
        for item in items:
            keys = [item["title"].casefold()]
            if item.get("slug"):
                keys.append("slug:" + item["slug"])
            for key in keys:
                title_index.setdefault(key, {})
                title_index[key].setdefault("categories", set()).add(slug)
                if item.get("author"):
                    title_index[key]["author"] = item["author"]
                if item.get("date"):
                    title_index[key]["date"] = item["date"]
            cat_map.setdefault(slug, set()).add(item["title"])
        # pagination page 2/3
        if not args.from_cache:
            for page_n in (2, 3):
                paged = row["url"].rstrip("/") + f"/page/{page_n}/"
                pname = f"{name}-p{page_n}"
                ppath = RAW_DIR / f"{pname}.md"
                try:
                    raw2 = fetch_cached(pname, paged, refresh)
                except Exception:
                    if ppath.exists():
                        ppath.unlink()
                    break
                extra = parse_category_listing(raw2)
                if not extra:
                    break
                for item in extra:
                    keys = [item["title"].casefold()]
                    if item.get("slug"):
                        keys.append("slug:" + item["slug"])
                    for key in keys:
                        title_index.setdefault(key, {})
                        title_index[key].setdefault("categories", set()).add(slug)
                        if item.get("author"):
                            title_index[key]["author"] = item["author"]
                        if item.get("date"):
                            title_index[key]["date"] = item["date"]

    media_urls: set[str] = set()
    for row in media_inv:
        media_urls.add(row["url"])
    media_urls.add("https://prelom.bg/wp-content/uploads/2022/ukraine.pdf")
    media_urls.add("https://prelom.bg/wp-content/uploads/2017/05/prelom-logo-est.jpg")

    written_posts = []
    written_pages = []
    redirects = []
    log(f"Fetching {len(posts_inv)} posts…")
    for row in posts_inv:
        url = row["url"]
        slug = slug_of(url)
        wp_id = row.get("id") or ""
        name = f"post-{wp_id}-{safe_filename(slug, wp_id or 'x')}"
        try:
            raw = fetch_cached(name, url, refresh)
        except Exception as exc:
            log(f"  post fail {slug}: {exc}")
            continue
        parsed = parse_jina_markdown(raw)
        title = parsed["title"] or slug
        meta = title_index.get("slug:" + slug) or title_index.get(title.casefold(), {})
        date = parsed["date"] or (meta.get("date") + "T12:00:00" if meta.get("date") else "")
        if date and len(date) == 10:
            date = date + "T12:00:00"
        author = meta.get("author") or extract_author_from_text(raw)
        categories = sorted(meta.get("categories") or [])
        body = rewrite_markdown_urls(strip_dead_markup(parsed["body"]))
        body = convert_youtube_links(body)
        media_urls |= collect_media_from_text(raw)
        excerpt = re.sub(r"\s+", " ", meaningful_text(body))[:240]
        date_prefix = (date or "2017-01-01")[:10]
        fm = {
            "title": title,
            "date": date or f"{date_prefix}T12:00:00",
            "permalink": f"/{slug}/",
            "slug": slug,
            "author": author,
            "author_slug": author,
            "excerpt": excerpt,
            "categories": categories,
            "tags": [],
            "wp_id": int(wp_id) if str(wp_id).isdigit() else wp_id,
            "comments": False,
        }
        filename = f"{date_prefix}-{safe_filename(slug, str(wp_id))}.md"
        path = POSTS_DIR / filename
        path.write_text(write_front_matter(fm, body), encoding="utf-8")
        written_posts.append(str(path.relative_to(ROOT)))
        log(f"  post {slug}")

    log(f"Fetching {len(pages_inv)} pages…")
    home_html_md = homepage_from_saved_html()
    for row in pages_inv:
        url = row["url"]
        slug = slug_of(url)
        wp_id = row.get("id") or ""
        is_home = path_of(url) in {"/", ""}
        name = "page-home" if is_home else f"page-{wp_id}-{safe_filename(slug or 'home', wp_id or 'x')}"
        try:
            raw = fetch_cached(name, url if not is_home else SITE + "/", refresh)
        except Exception as exc:
            log(f"  page fail {slug or '/'}: {exc}")
            raw = ""
        parsed = parse_jina_markdown(raw) if raw else {"title": "", "date": "", "body": ""}
        title = parsed["title"] or ("Утре е сега!" if is_home else slug)
        meta = title_index.get("slug:" + slug) or title_index.get(title.casefold(), {})
        date = parsed["date"] or ""
        body = home_html_md if is_home and home_html_md else rewrite_markdown_urls(parsed["body"])
        body = apply_special_page(slug or "home", body)
        media_urls |= collect_media_from_text(raw)
        text = meaningful_text(body)
        if (slug in REDIRECT_IF_EMPTY or (len(text) < 40 and slug not in KEEP_PAGES_WITH_EMBEDS and not is_home)):
            if slug and slug not in KEEP_PAGES_WITH_EMBEDS:
                fm = {
                    "title": title or slug,
                    "permalink": f"/{slug}/",
                    "slug": slug,
                    "layout": "single",
                    "redirect_to": "/contact/",
                    "sitemap": False,
                    "wp_id": int(wp_id) if str(wp_id).isdigit() else wp_id,
                }
                filename = f"{safe_filename(slug, str(wp_id))}.md"
                path = PAGES_DIR / filename
                path.write_text(write_front_matter(fm, ""), encoding="utf-8")
                written_pages.append(str(path.relative_to(ROOT)))
                redirects.append(f"/{slug}/")
                log(f"  redirect {slug} -> /contact/")
                continue
        excerpt = re.sub(r"\s+", " ", text)[:240]
        if is_home:
            dest = ROOT / "index.md"
            fm = {
                "title": title,
                "permalink": "/",
                "layout": "single",
                "author_profile": False,
                "comments": False,
                "share": False,
                "header": {"teaser": "/wp-content/uploads/2024/01/100X100-Bulgaria.png"},
                "wp_id": int(wp_id) if str(wp_id).isdigit() else wp_id,
            }
            dest.write_text(write_front_matter(fm, body), encoding="utf-8")
            written_pages.append("index.md")
            log("  page /")
            continue
        fm = {
            "title": title or slug,
            "permalink": f"/{slug}/",
            "slug": slug,
            "layout": "single",
            "author_profile": False,
            "comments": False,
            "wp_id": int(wp_id) if str(wp_id).isdigit() else wp_id,
        }
        if date:
            fm["date"] = date
        if excerpt:
            fm["excerpt"] = excerpt
        if meta.get("categories"):
            fm["categories"] = sorted(meta["categories"])
        filename = f"{safe_filename(slug, str(wp_id))}.md"
        path = PAGES_DIR / filename
        path.write_text(write_front_matter(fm, body), encoding="utf-8")
        written_pages.append(str(path.relative_to(ROOT)))
        log(f"  page {slug}")

    log("Writing taxonomy archives…")
    tax_written = []
    for row in cats_inv:
        slug = slug_of(row["url"])
        title = CATEGORY_NAMES.get(slug, slug)
        tax_written.append(str(write_tax_page("category", slug, title).relative_to(ROOT)))
    for row in tags_inv:
        slug = slug_of(row["url"])
        tax_written.append(str(write_tax_page("tag", slug, slug).relative_to(ROOT)))
    author_titles = {"admin": "Админ", "admin3": "Поликсения"}
    for row in authors_inv:
        slug = slug_of(row["url"])
        tax_written.append(str(write_tax_page("author", slug, author_titles.get(slug, slug)).relative_to(ROOT)))

    media_results: list[dict[str, Any]] = []
    if not args.skip_media:
        jobs: list[tuple[str, Path]] = []
        seen: set[str] = set()
        for url in sorted(media_urls):
            rel = original_rel(url)
            if not rel or rel in seen:
                continue
            seen.add(rel)
            dest = UPLOADS_DIR / rel
            src = "https://prelom.bg/wp-content/uploads/" + rel
            jobs.append((src, dest))
        log(f"Downloading {len(jobs)} media files…")
        for i, (src, dest) in enumerate(jobs, 1):
            ext = dest.suffix.lower()
            if ext in {".pdf", ".doc", ".docx", ".xls", ".xlsx"}:
                size, err = download_binary_fallback(src, dest)
            else:
                size, err = download_via_weserv(src, dest)
                if err:
                    size, err2 = download_binary_fallback(src, dest)
                    err = None if size else (err or err2)
            media_results.append({"url": src, "path": str(dest.relative_to(ROOT)), "bytes": size, "error": err})
            if i % 10 == 0 or err:
                log(f"  media {i}/{len(jobs)} {dest.name} {size} {err or 'ok'}")
        MEDIA_MANIFEST.write_text(json.dumps(media_results, ensure_ascii=False, indent=2), encoding="utf-8")

        # Site logo
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        logo_src = UPLOADS_DIR / "2017" / "05" / "prelom-logo-est.jpg"
        logo_dest = IMAGES_DIR / "logo.jpg"
        if logo_src.exists() and not logo_dest.exists():
            logo_dest.write_bytes(logo_src.read_bytes())

    ok_media = [m for m in media_results if not m.get("error") and m.get("bytes", 0) > 0]
    failed_media = [m for m in media_results if m.get("error")]
    total_bytes = sum(m.get("bytes") or 0 for m in ok_media)
    report = {
        "source": SITE,
        "migrated_posts": len(written_posts),
        "migrated_pages": len(written_pages),
        "redirects": redirects,
        "taxonomy_pages": len(tax_written),
        "media_files": len(ok_media),
        "media_bytes": total_bytes,
        "media_failed": failed_media,
        "written_posts": written_posts,
        "written_pages": written_pages,
        "notes": {
            "fetch": "Jina reader markdown (Cloudflare blocks direct datacenter fetches)",
            "dropped": [
                "comments",
                "WP search",
                "deal.ai chat widget",
                "raw PTA / Jetpack / MC4WP shortcodes",
                "dead charter-bg Mautic script",
            ],
        },
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(
        f"Done. posts={len(written_posts)} pages={len(written_pages)} "
        f"redirects={len(redirects)} media={len(ok_media)} "
        f"({total_bytes/1_000_000:.1f} MB) failed_media={len(failed_media)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
