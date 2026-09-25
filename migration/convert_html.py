#!/usr/bin/env python3
"""Convert cached public HTML in migration/raw/html/ into Jekyll Markdown."""

from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

import migrate as M

HTML_DIR = M.RAW_DIR / "html"

CAT_NAME_TO_SLUG = {
    "поучение": "pouchenie",
    "общи": "obshti",
    "апостолски": "apostolski",
    "позиции": "positions",
    "english": "english",
    "пророчески": "prorocheski",
    "видео": "videochat",
    "архив": "архив",
    "archives": "archives",
    "дейности": "дейности",
    "pouchenie": "pouchenie",
    "obshti": "obshti",
    "apostolski": "apostolski",
    "positions": "positions",
    "prorocheski": "prorocheski",
    "videochat": "videochat",
}

KNOWN_CAT_SLUGS = set(M.CATEGORY_NAMES)
WAYBACK_RE = re.compile(
    r"https?://web\.archive\.org/web/\d+[a-z_]*/(https?://[^\s\"'<>]+)",
    re.I,
)
WAYBACK_REL_RE = re.compile(
    r"/web/\d+[a-z_]*/(https?://[^\s\"'<>]+)",
    re.I,
)
ARTICLE_CAT_RE = re.compile(r"\bcategory-([A-Za-z0-9_\-\u0400-\u04FF]+)")
ARTICLE_TAG_RE = re.compile(r"\btag-([A-Za-z0-9_\-\u0400-\u04FF]+)")


def strip_wayback(url: str) -> str:
    if not url:
        return url
    m = WAYBACK_RE.search(url)
    if m:
        return m.group(1)
    m = WAYBACK_REL_RE.search(url)
    if m:
        return m.group(1)
    return url


def clean_html(html: str) -> str:
    def repl(match: re.Match) -> str:
        return strip_wayback(match.group(0))

    html = WAYBACK_RE.sub(lambda m: m.group(1), html)
    html = WAYBACK_REL_RE.sub(lambda m: m.group(1), html)
    return html


def extract_title(soup: BeautifulSoup) -> str:
    for sel in ("h1.entry-title", "h1.page-title", "meta[property='og:title']"):
        el = soup.select_one(sel)
        if not el:
            continue
        if el.name == "meta":
            title = (el.get("content") or "").strip()
        else:
            title = el.get_text(" ", strip=True)
        title = re.sub(r"\s*[–—|-]\s*Християнски Център Прелом.*$", "", title).strip()
        if title and title != "Християнски Център Прелом":
            return title
    t = soup.title.get_text(" ", strip=True) if soup.title else ""
    return re.sub(r"\s*[–—|-]\s*Християнски Център Прелом.*$", "", t).strip()


def extract_date(soup: BeautifulSoup) -> str:
    el = soup.select_one("time.entry-date[datetime], time[datetime]")
    if el and el.get("datetime"):
        return el["datetime"].strip()
    return ""


def extract_author(soup: BeautifulSoup) -> str:
    el = soup.select_one(".author a, .byline a, a[rel=author]")
    if el:
        return M.author_slug(el.get_text(" ", strip=True))
    return "admin"


def extract_excerpt(soup: BeautifulSoup, body: str) -> str:
    og = soup.select_one("meta[property='og:description']")
    if og and og.get("content"):
        text = re.sub(r"\s+", " ", og["content"]).strip()
        if text and text not in {"Visit the post for more.", "Add your Typeform title here"}:
            return text[:240]
    return re.sub(r"\s+", " ", M.meaningful_text(body))[:240]


def extract_taxonomies(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    cats: set[str] = set()
    tags: set[str] = set()
    article = soup.select_one("article")
    classes = " ".join(article.get("class", []) if article else [])
    body_classes = soup.body.get("class", []) if soup.body else []
    classes += " " + " ".join(body_classes)
    for slug in ARTICLE_CAT_RE.findall(classes):
        if slug in KNOWN_CAT_SLUGS or slug in CAT_NAME_TO_SLUG:
            cats.add(CAT_NAME_TO_SLUG.get(slug.lower(), slug))
    for slug in ARTICLE_TAG_RE.findall(classes):
        if slug.isdigit():
            continue
        tags.add(slug)
    for a in soup.select("a[rel='category tag'], a[rel=category], .cat-links a"):
        href = a.get("href") or ""
        path = M.path_of(href)
        if "/category/" in path:
            slug = path.rstrip("/").split("/")[-1]
            if slug:
                cats.add(slug)
        else:
            name = a.get_text(" ", strip=True)
            mapped = CAT_NAME_TO_SLUG.get(name.casefold())
            if mapped:
                cats.add(mapped)
    for a in soup.select("a[rel=tag], .tags-links a"):
        href = a.get("href") or ""
        path = M.path_of(href)
        if "/tag/" in path:
            slug = path.rstrip("/").split("/")[-1]
            if slug:
                tags.add(slug)
    return sorted(cats), sorted(tags)


def protect_extra_embeds(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for widget in soup.select(".typeform-widget"):
        data_url = widget.get("data-url") or ""
        if data_url:
            iframe = soup.new_tag("iframe")
            iframe["src"] = data_url
            iframe["title"] = "Typeform"
            iframe["loading"] = "lazy"
            iframe["style"] = "width:100%;min-height:480px;border:0"
            widget.replace_with(iframe)
    for script in list(soup.find_all("script")):
        src = script.get("src") or ""
        if "spark.adobe.com/page-embed.js" in src:
            script.decompose()
            continue
        if "embed.typeform.com" in src or "typeform.com/embed" in src:
            script.decompose()
            continue
        if "sermon.net" in src or "iframeResizer" in src:
            script.decompose()
    for a in soup.select("a.asp-embed-link"):
        href = a.get("href") or "https://spark.adobe.com/"
        img = a.find("img")
        alt = (img.get("alt") if img else None) or a.get_text(" ", strip=True) or "Adobe Spark"
        iframe = soup.new_tag("iframe")
        iframe["src"] = href.rstrip("/") + "/embed.html" if "/page/" in href else href
        iframe["title"] = alt
        iframe["loading"] = "lazy"
        iframe["style"] = "width:100%;min-height:640px;border:0"
        # Keep a visible fallback link plus the original spark image if present
        wrapper = soup.new_tag("p")
        if img:
            img["src"] = img.get("src") or href
            wrapper.append(img)
            wrapper.append(soup.new_tag("br"))
        link = soup.new_tag("a", href=href)
        link.string = alt
        link["target"] = "_blank"
        link["rel"] = "noopener"
        wrapper.append(link)
        a.replace_with(wrapper)
    return str(soup)


def convert_entry(html: str) -> str:
    html = clean_html(html)
    html = protect_extra_embeds(html)
    return M.html_to_markdown(html)


def html_file_for(row: dict) -> Path:
    kind = row["type"]
    ident = row.get("id") or "-"
    slug = M.slug_of(row["url"])
    if kind == "post":
        return HTML_DIR / f"post-{ident}-{M.safe_filename(slug, ident)}.html"
    if M.path_of(row["url"]) in {"/", ""}:
        return HTML_DIR / "page-home.html"
    return HTML_DIR / f"page-{ident}-{M.safe_filename(slug or 'home', ident)}.html"


def apply_page_specials(slug: str, body: str, soup: BeautifulSoup) -> str:
    body = M.strip_dead_markup(body)
    if slug == "donate":
        return "{% include paypal-donate.html %}\n"
    if slug == "newsletter":
        return "{% include mailchimp-form.html %}\n"
    if slug == "contact":
        return "{% include contact-form.html %}\n"
    if slug == "ukraine":
        pdf = "{{ site.baseurl }}/wp-content/uploads/2022/ukraine.pdf"
        return (
            "Документ за Украйна (PDF).\n\n"
            f"[Изтеглете документа (PDF)]({pdf})\n"
        )
    if slug == "men":
        target = "{{ site.baseurl }}/първо-са-мъжете/"
        return f"[Първо са мъжете]({target})\n"
    if slug == "justice21" and "contact-form.html" not in body:
        body = body.rstrip() + "\n\n{% include contact-form.html %}\n"
    if slug == "pokana220319":
        body = M.strip_dead_markup(body)
        body = re.sub(r"Моля изпратете вашият отговор[^\n]*", "", body)
        body = body.rstrip() + "\n\nЗа връзка използвайте [контактите]({{ site.baseurl }}/contact/).\n"
    if slug == "volunteer-signup":
        body = M.strip_dead_markup(body)
        body = re.sub(r"Логин и регистрация[^\n]*", "", body)
        body = body.rstrip() + (
            "\n\nСистемата за записване вече не работи. "
            "Пишете ни през [контактите]({{ site.baseurl }}/contact/).\n"
        )
    if slug == "charter-bg":
        body = M.strip_dead_markup(body)
    return body


def main() -> int:
    inventory = M.load_inventory()
    posts_inv = [r for r in inventory if r["type"] == "post"]
    pages_inv = [r for r in inventory if r["type"] == "page"]
    cats_inv = [r for r in inventory if r["type"] == "category"]
    tags_inv = [r for r in inventory if r["type"] == "tag"]
    authors_inv = [r for r in inventory if r["type"] == "author"]
    media_inv = [r for r in inventory if r["type"] == "media"]

    M.reset_generated()
    written_posts = []
    written_pages = []
    redirects = []
    media_urls = {r["url"] for r in media_inv}
    media_urls.add("https://prelom.bg/wp-content/uploads/2022/ukraine.pdf")

    for row in posts_inv:
        slug = M.slug_of(row["url"])
        wp_id = row.get("id") or ""
        path = html_file_for(row)
        if not path.exists():
            print(f"MISSING html {path.name}", flush=True)
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")
        title = extract_title(soup) or slug
        date = extract_date(soup) or "2017-01-01T12:00:00"
        author = extract_author(soup)
        if not soup.select_one(".author a, a[rel=author]"):
            author = "admin"
        cats, tags = extract_taxonomies(soup)
        ec = soup.select_one(".entry-content")
        body = convert_entry(str(ec) if ec else "")
        media_urls |= M.collect_media_from_text(str(ec) if ec else "")
        excerpt = extract_excerpt(soup, body)
        if excerpt.strip() in {"Visit the post for more.", "Add your Typeform title here"}:
            excerpt = re.sub(r"\s+", " ", M.meaningful_text(body))[:240]
        date_prefix = date[:10]
        fm = {
            "title": title,
            "date": date,
            "permalink": f"/{slug}/",
            "slug": slug,
            "author": author,
            "author_slug": author,
            "excerpt": excerpt,
            "categories": cats,
            "tags": tags,
            "wp_id": int(wp_id) if str(wp_id).isdigit() else wp_id,
            "comments": False,
        }
        filename = f"{date_prefix}-{M.safe_filename(slug, str(wp_id))}.md"
        dest = M.POSTS_DIR / filename
        dest.write_text(M.write_front_matter(fm, body), encoding="utf-8")
        written_posts.append(str(dest.relative_to(M.ROOT)))
        print(f"post {slug}", flush=True)

    for row in pages_inv:
        url = row["url"]
        slug = M.slug_of(url)
        wp_id = row.get("id") or ""
        is_home = M.path_of(url) in {"/", ""}
        path = html_file_for(row)
        # Prefer the earlier full homepage capture when present
        if is_home and (M.RAW_DIR / "page-home-entry.html").exists():
            entry_html = (M.RAW_DIR / "page-home-entry.html").read_text(encoding="utf-8")
            soup = BeautifulSoup(
                path.read_text(encoding="utf-8", errors="replace") if path.exists() else entry_html,
                "lxml",
            )
            body = convert_entry(entry_html)
            title = "Утре е сега!"
        else:
            if not path.exists():
                print(f"MISSING html page {slug}", flush=True)
                continue
            soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")
            title = extract_title(soup) or ("Утре е сега!" if is_home else slug)
            ec = soup.select_one(".entry-content")
            body = convert_entry(str(ec) if ec else "")
            media_urls |= M.collect_media_from_text(str(ec) if ec else "")
        cats, tags = extract_taxonomies(soup)
        body = apply_page_specials(slug or "home", body, soup)
        text = M.meaningful_text(body)
        keep_short = {"men", "ukraine", "защо-прелом", "insidevideoblog", "видео-партньорство-заедно", "най-новата-информация-26-януари", "програма-за-подготовка-на-млади-хора"}
        if slug in M.REDIRECT_IF_EMPTY or (
            len(text) < 40
            and slug not in M.KEEP_PAGES_WITH_EMBEDS
            and slug not in keep_short
            and not is_home
            and "responsive-embed" not in body
            and "iframe" not in body
            and "spark.adobe.com" not in body
            and "typeform.com" not in body
            and "rumble.com" not in body
        ):
            if slug and slug not in M.KEEP_PAGES_WITH_EMBEDS:
                fm = {
                    "title": title or slug,
                    "permalink": f"/{slug}/",
                    "slug": slug,
                    "layout": "single",
                    "redirect_to": "/contact/",
                    "sitemap": False,
                    "wp_id": int(wp_id) if str(wp_id).isdigit() else wp_id,
                }
                dest = M.PAGES_DIR / f"{M.safe_filename(slug, str(wp_id))}.md"
                dest.write_text(M.write_front_matter(fm, ""), encoding="utf-8")
                written_pages.append(str(dest.relative_to(M.ROOT)))
                redirects.append(f"/{slug}/")
                print(f"redirect {slug} -> /contact/", flush=True)
                continue
        excerpt = extract_excerpt(soup, body)
        if excerpt.strip() in {"Visit the post for more.", "Add your Typeform title here"}:
            excerpt = re.sub(r"\s+", " ", M.meaningful_text(body))[:240]
        if is_home:
            dest = M.ROOT / "index.md"
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
            dest.write_text(M.write_front_matter(fm, body), encoding="utf-8")
            written_pages.append("index.md")
            print("page /", flush=True)
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
        date = extract_date(soup)
        if date:
            fm["date"] = date
        if excerpt:
            fm["excerpt"] = excerpt
        if cats:
            fm["categories"] = cats
        if tags:
            fm["tags"] = tags
        dest = M.PAGES_DIR / f"{M.safe_filename(slug, str(wp_id))}.md"
        dest.write_text(M.write_front_matter(fm, body), encoding="utf-8")
        written_pages.append(str(dest.relative_to(M.ROOT)))
        print(f"page {slug}", flush=True)

    tax_written = []
    for row in cats_inv:
        slug = M.slug_of(row["url"])
        title = M.CATEGORY_NAMES.get(slug, slug)
        tax_written.append(str(M.write_tax_page("category", slug, title).relative_to(M.ROOT)))
    for row in tags_inv:
        slug = M.slug_of(row["url"])
        tax_written.append(str(M.write_tax_page("tag", slug, slug).relative_to(M.ROOT)))
    author_titles = {"admin": "Админ", "admin3": "Поликсения"}
    for row in authors_inv:
        slug = M.slug_of(row["url"])
        tax_written.append(
            str(M.write_tax_page("author", slug, author_titles.get(slug, slug)).relative_to(M.ROOT))
        )

    report = {
        "source": M.SITE,
        "migrated_posts": len(written_posts),
        "migrated_pages": len(written_pages),
        "redirects": redirects,
        "taxonomy_pages": len(tax_written),
        "written_posts": written_posts,
        "written_pages": written_pages,
        "media_referenced": sorted(media_urls),
        "notes": {
            "fetch": "Public HTML via allorigins (Cloudflare blocks datacenter IPs)",
            "dropped": [
                "comments",
                "WP search",
                "deal.ai chat widget",
                "raw PTA / Jetpack / MC4WP shortcodes",
                "dead charter-bg Mautic script",
            ],
        },
    }
    M.REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Done. posts={len(written_posts)} pages={len(written_pages)} "
        f"redirects={len(redirects)} tax={len(tax_written)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
