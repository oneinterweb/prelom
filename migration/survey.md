# prelom.bg — pre-migration survey (WordPress → Jekyll / GitHub Pages)

Survey date: 2026-09-25 (Dubai time). Read-only: no changes were made to the site. Raw captures are in `raw/`.

## 0. Important caveat: the REST API and XML-RPC are blocked, so this survey uses the public site only
- **WP Cerber Security 9.0** returns **HTTP 403 "We're sorry, you are not allowed to proceed"** for `/wp-json/*` and `/?rest_route=` requests. That happens with and without the admin application password (Basic auth). `/xmlrpc.php` and `/wp-login.php` also return 403. Only `/wp-json/oembed/*` is allowed.
- So the following **could not be collected**: `/wp/v2/plugins`, `/wp/v2/types`, draft/private/pending counts, the user list, and exact media `filesize` values.
- Instead, the counts below come from the public HTML, the sitemaps, and a probe of `/?p=1…1800`. That probe finds **every published** post, page, and attachment, because WordPress redirects each valid ID to its canonical URL.
- Cerber also rate-limits (HTTP 429) after a few dozen quick requests. Crawl at about 1 request per second.
- To get the full data (drafts, private items, the exact plugin list, and a WXR export), pick one of these:
  - (a) In the WP admin, allow REST for the app password or whitelist our IP under Cerber → Hardening → "Disable REST API"
  - (b) Run Tools → Export (WXR)
  - (c) Use cPanel file/DB access
- The site has **WP_DEBUG display on**. PHP notices (`_load_textdomain_just_in_time … wp-cerber`) are printed before every response, which exposes the server path `/home/yszcgrq/public_html`. This also breaks the main RSS feed: `/feed/` 301-redirects to itself in a loop. Category feeds still work.

## 1. Platform
| Item | Value |
|---|---|
| WordPress | **7.1.2** (from the generator meta tag and asset `ver=` values) |
| Theme | **PH News Bulletin 1.0.2.2** (PixaHive, based on Underscores). **No parent/child theme.** Page templates in use: default (16), centered (11), fullwidth (4) |
| Page builder | **None.** Content is Gutenberg blocks (cover, paragraph, heading, embed, button, file, image) plus older Classic-editor HTML |
| Hosting | cPanel account `yszcgrq` on 162.246.59.205 (oneinterweb server), behind a Cloudflare custom hostname `yszctuqddd.wpdns.site`. There is also a staging copy at `yszctuqddd-staging.wpdns.site` (it shows up in comment GUIDs) |

### Plugins (the authenticated list was not available; this is what the evidence shows)
| Plugin | Version (readme) | Status (inferred) |
|---|---|---|
| WP Cerber Security, Anti-spam & Malware Scan | 9.0 | **Active** (blocks REST; adds anti-spam hidden fields to forms) |
| XML Sitemap & Google News (xml-sitemap-feed) | 5.7.7 | **Active** (serves the sitemaps) |
| LeadConnector (GoHighLevel) | 4.0.6 (asset ver) | **Active** (its CSS loads on every page) |
| Compact WP Audio Player | 1.9.15 | **Active** (assets load site-wide) but **not used** in any published content |
| Jetpack | 16.2 | Installed, **inactive/disconnected**: `[contact-form]` shortcodes show as raw text, and the Jetpack contact-form block on /contact/ is empty |
| MC4WP: Mailchimp for WordPress | 4.14.1 | Installed, **inactive**: `[mc4wp_form]` shows as raw text on /pokana220319/ |
| Volunteer Sign Up Sheets (pta-volunteer-sign-up-sheets) | 5.5.9 | Installed, **inactive**: `[pta_sign_up_sheet]` shows as raw text |
| Member Directory and Contact Form (pta-member-directory) | trunk | Installed, **inactive**: `[pta_member_directory]` / `[pta_member_contact]` show as raw text |
| Some "categories for pages" functionality | ? | Active: 10 **pages** are assigned to categories and appear in category archives |

Probed and **not present**: Contact Form 7, WPForms, Gravity Forms, Patreon Connect, MemberPress, Restrict Content, Paid Memberships Pro, Members, Password Protected, Wordfence, Yoast, RankMath, Polylang, WPML, Elementor, WPBakery, Classic Editor, Akismet, The Events Calendar, GiveWP, UpdraftPlus, WP Mail SMTP, LiteSpeed Cache.

Third-party scripts on every page: `api.marketing.deal.ai/widget.js?appId=c491cba2-…` (chat/marketing widget, loaded 3 times), jQuery 3.7.1 plus migrate, and theme libraries (owl-carousel, acmeticker, sidr, bootstrap, fontawesome).

## 2. Content counts (published only)
| Type | Count | Notes |
|---|---|---|
| Posts | **34** | All have Cyrillic slugs. 26 from 2017, 5 from 2019, 1 each from 2020, 2024, and 2025 |
| Pages | **31** | Includes the static front page (ID 1511). 7 have Cyrillic slugs and 24 have Latin slugs. 10 are assigned to categories |
| Attachments (media library items with public attachment pages) | **65** | |
| Custom post types | **none found** | Body classes show only post, page, and attachment. The `/wp/v2/types` endpoint was blocked |
| Categories | **10** | pouchenie (Поучения, 28 items), obshti (27), apostolski (25), positions (3), english (2), prorocheski (2), videochat (2), архив (1), archives (1), дейности (1). Counts include pages |
| Tags | **206** | 190 have Cyrillic slugs, e.g. `/tag/духовно-тяло/` |
| Comments | **4** approved | All on page /statement-churchsplit-2017bg/, from June–July 2017. Comment forms are still open on about 114 posts/pages/attachments |
| Authors | **2 with archives** | `admin` ("Админ", 31 posts) and `admin3` ("Поликсения", 2 posts). One post (2017-09-10) has an author with an empty nicename |
| Drafts / private / pending | **unknown** | Requires REST/admin access (blocked). ID gaps are normal (revisions, autosaves, deleted items) |

## 3. Permalinks and URLs
- Structure: **`/%postname%/`** for both posts and pages. The category base is `/category/` and the tag base is `/tag/`. Attachment pages use `/<parent-slug>/<attachment-slug>/`.
- Post slugs are **Cyrillic and percent-encoded**, e.g. `/ден-1-духовно-тяло/` = `/%d0%b4%d0%b5%d0%bd-1-…/`. Many are truncated by WP at about 200 bytes, e.g. `/публична-подкрепа-от-вярващи-от-14-декем/`. Jekyll needs `permalink:` in each file's front matter to keep these exact URLs.
- Sitemaps: `/sitemap.xml` (same as `/wp-sitemap.xml`) is an index from XML Sitemap & Google News. It links to sitemap-posttype-post (34), sitemap-taxonomy-category (10), sitemap-taxonomy-post_tag (206), sitemap-author (2), and sitemap-news (1, the homepage). `sitemap_index.xml` returns 404. **There is no page sitemap, so none of the 31 pages are in the sitemap.**
- **`urls.txt`: 253 unique URLs** from the sitemaps, decoded to Cyrillic.
- **`urls_all.tsv`: full inventory of 348 URLs** (34 posts, 31 pages, 10 categories, 206 tags, 2 authors, 65 media files). Use this one for redirect and parity checks.
- The primary menu item "Начало" links to **`https://yszctuqddd.wpdns.site`** (the origin hostname) instead of `/`. This should be fixed in the new site.

### Pages
| ID | Path | Title | Words | Embeds / forms |
|---|---|---|---|---|
| 59 | /събития/ | Събития | 1 | empty (events plugin removed?) |
| 65 | /donate/ | Дарения | 10 | **PayPal** donate form (www.paypal.com/cgi-bin/webscr) |
| 70 | /creeds/ | Верую | 3071 | |
| 123 | /volunteers/ | Доброволци | 2 | broken `[pta_member_directory]` |
| 125 | /volunteer-signup/ | Записване за доброволна помощ | 130 | broken `[pta_sign_up_sheet]` (asks users to register/log in) |
| 127 | /contact-volunteer/ | Връзка с доброволци | 4 | broken `[pta_member_contact]` |
| 142 | /audio/ | Проповеди – аудио | 18 | **sermon.net** player iframe |
| 152 | /video/ | Видео | 28 | YouTube playlist |
| 158 | /media/ | Аудио и видео проповеди и поучения | 34 | YouTube playlist + sermon.net widget |
| 185 | /statement-churchsplit-2017bg/ | Разцепление, изцеление, единение | 6811 | 4 comments |
| 191 | /charter/ | Charter | 1551 | |
| 195 | /charter-bg/ | Харта | 1989 | script `//prelom.bg/news/form/generate.js?id=2` (**404, dead** Mautic-style form) |
| 233 | /newsletter/ | Новини | 33 | **Mailchimp** embedded form → prelom.us7.list-manage.com (u=7cac460297578bb4e3a8622c0, id=5fb9dac49e) |
| 478 | /assessment2017/ | Въпросник 2017 | 24 | Typeform (infobank.typeform.com/to/ZrXqyF) |
| 552 | /testimony-regarding-…-kurdomanov/ | Testimony Regarding … Split | 3382 | |
| 562 | /kaloyan-kurdomanov-exibit-a-…/ | Exhibit A | 70 | image-based |
| 569 | /публична-подкрепа-от-вярващи-от-14-декем/ | Публична подкрепа… | 3655 | |
| 582 | /exhibit-b-pastor-kurdomanov-…/ | Exhibit B | 1002 | |
| 599 | /защо-прелом/ | Защо Прелом? | 2 | YouTube playlist |
| 603 | /insidevideoblog/ | Вътрешен видео блог | 3 | YouTube playlist |
| 688 | /justice21/ | Справедливост 21 | 400 | Vimeo + Facebook video, broken Jetpack `[contact-form]` |
| 725 | /програма-за-подготовка-на-млади-хора/ | Програма за подготовка на млади хора | 6 | Adobe Spark page embed |
| 900 | /pokana220319/ | Покана за събитие | 14 | YouTube, broken `[mc4wp_form]` |
| 1069 | /dr-joseph-shulam-registration-form/ | Регистрация … д-р Йосиф Шулам (Oct 2019) | 52 | Typeform widget (veselintonov.typeform.com/to/NVbRpE) |
| 1358 | /ukraine/ | Ukraine | 7 | meta-refresh to /wp-content/uploads/2022/ukraine.pdf (7.5 MB) |
| 1511 | / (front page) | Утре е сега! | 539 | YouTube + **threefold.life CRM form** |
| 1532 | /видео-партньорство-заедно/ | ВИДЕО: Партньорство заедно | 3 | Rumble |
| 1537 | /най-новата-информация-26-януари/ | Най-новата информация – 26 януари | 5 | Rumble |
| 1555 | /men/ | Мъжка дума | 6 | link to wp.me short URL |
| 1562 | /първо-са-мъжете/ | Първо са мъжете | 712 | |
| 1596 | /contact/ | Свържете се | 2 | **empty** Jetpack contact-form block (renders nothing) |

## 4. Gated, paid, or member content
- **None found.** There are **0 password-protected** posts or pages (no `post-password-form` on any of the 65 published posts/pages). There is **no Patreon, MemberPress, PMPro, or Restrict Content** plugin (their plugin directories return 404), and no "members only / premium / patreon" markers in any content.
- The only login-dependent feature is the dead volunteer sign-up system (PTA plugins, inactive). It is not really gated content.
- Unlike apostolos.bg (183 Patreon-locked posts), prelom.bg has **0 affected posts**. One caveat: drafts and private posts cannot be seen without admin access.

## 5. Forms, embeds, multilingual
**Forms that work today and where they send data:**
1. Front page: `<script src="https://threefold.life/crm/form/generate.js?id=36">` (external CRM form, Threefold/Mautic-style)
2. /newsletter/: Mailchimp → `prelom.us7.list-manage.com/subscribe/post?u=7cac460297578bb4e3a8622c0&id=5fb9dac49e`
3. /donate/: PayPal `webscr` donate button
4. /assessment2017/ and /dr-joseph-shulam-registration-form/: Typeform embeds (these look outdated, from 2017 and 2019)
5. WordPress comment forms (wp-comments-post.php) and the search form (`/?s=`). These need a replacement or removal on a static site.

**Broken or dead forms:** Jetpack contact form (/contact/, /justice21/), MC4WP (/pokana220319/), PTA volunteer sheets (3 pages), and `prelom.bg/news/form/generate.js?id=2` (404) on /charter-bg/.

**Embeds:** 11 YouTube iframes (single videos and playlists; channel @PrelomCenter), 2 Rumble, 1 Vimeo, 1 Facebook video, 2 sermon.net (audio sermons: Prelom.sermon.net), Adobe Spark, and Typeform. The site-wide deal.ai widget and the LeadConnector plugin are also present. There are **no calendar/events plugins** (/събития/ is empty) and **no livestream widget** beyond the YouTube links.

**Multilingual:** none (no WPML or Polylang). There is some English content in the "english" category (charter, testimony, exhibits).

## 6. Media
- There are 65 attachment items, and all 65 original files returned HTTP 200. Their total size is **12.1 MB**.
- Counting every distinct original file referenced in content (70 files, including `ukraine.pdf` at 7.46 MB and a few hotlinked originals), the total is **19.7 MB**.
- By type: about 100 jpg references, 25 png, 3 doc, 1 pdf, and 2 jpeg.
- Largest files: ukraine.pdf (7.5 MB) and freely-36201.jpg (2.2 MB).
- **Already-404 media: 0 of 131** HEAD-checked URLs (the check covered 100% of referenced originals). Unknown files do return a real 404, so this result is reliable.
- Estimated full `wp-content/uploads` size including WordPress-generated thumbnails: about **35–50 MB**. That fits easily within GitHub Pages limits.
- The theme's `/wp-content/uploads/` directory listing is disabled (404), so orphan files that aren't referenced anywhere could not be counted.

## 7. Menus and homepage
- **Primary menu** (header and mobile "sidr" menu; flat, no submenus):
  - Начало → `https://yszctuqddd.wpdns.site` (bug)
  - Поучения → /category/pouchenie/
  - YouTube → youtube.com/@PrelomCenter
  - Facebook → facebook.com/prelomcenter
  - X → https://2x1.io/3foldonX
- **Homepage:** a **static page** (ID 1511, "Утре е сега!"), not a list of latest posts. Its sections, in order:
  1. An H1 with a long manifesto essay by Георги Бакалов, founder. It ends with "…в събота от 17 часа на събирането ни в молитвен център Кармил".
  2. An H1 "Включи се в промяната!" with the threefold.life CRM signup form embedded.
  3. A cover block with the "100X100 Bulgaria" image.
  4. A YouTube embed (O3Tq9Ef2piE).
  - The sidebar (search and "Последни публикации") exists in the markup but is hidden (`d-none`). The theme's news ticker and carousel features are not visibly used.

## 8. DNS (checked 2026-09-25)
| Name | Type | Value |
|---|---|---|
| prelom.bg | NS | **ns1.oneinterweb.com (162.246.59.205), ns2.oneinterweb.com (162.246.59.206)**. These are **not Cloudflare** nameservers; they are self-hosted cPanel/WHM DNS. SOA: ns1.oneinterweb.com, dns.prelom.bg, serial 2026092502 |
| prelom.bg | A | 104.18.185.50 (a Cloudflare anycast IP) |
| prelom.bg | AAAA | none |
| www.prelom.bg | CNAME | **yszctuqddd.wpdns.site** (origin custom hostname; its zone uses Cloudflare NS piers/sara) → 104.17.144.110 / 104.17.145.110. www 301-redirects to https://prelom.bg/ |
| prelom.bg | MX | **1 smtp.google.com** (Google Workspace), **preserve** |
| prelom.bg | TXT | **SPF**: `v=spf1 ip4:162.246.59.205 +a +mx +ip4:185.11.147.19 +ip4:185.62.188.4 +ip4:185.61.137.198 +ip4:185.61.137.196 +ip4:185.61.137.189 +ip4:185.61.137.175 include:relay.mailchannels.net include:_spf.mlsend.com ~all`, **preserve** |
| prelom.bg | TXT | `google-site-verification=KNE5aHAA4nxgfVvsirMb88F8Q17z4FuJgsKyVQSst1w`, **preserve** |
| _dmarc.prelom.bg | TXT | `v=DMARC1;p=reject;sp=none;adkim=r;aspf=r;pct=100;fo=0;rf=afrf;ri=86400`, **preserve** |
| google._domainkey.prelom.bg | TXT | Google Workspace DKIM (v=DKIM1; k=rsa; 2048-bit key), **preserve** |
| webmail / cpanel / autodiscover.prelom.bg | A | 162.246.59.205 (cPanel proxy subdomains) |
| ftp.prelom.bg | CNAME | prelom.bg |
| CAA | — | none |

**Cutover notes:**
- Keep the MX, SPF, DMARC, DKIM (google._domainkey), and google-site-verification records exactly as they are.
- Change only the apex A record and the www CNAME:
  - Apex A → GitHub Pages IPs 185.199.108–111.153 (and AAAA 2606:50c0:8000–8003::153)
  - www CNAME → `<user>.github.io`
- Note that **the SPF includes the apex's `+a`**. Once the apex A points at GitHub, `+a` will authorise GitHub's IPs. That is harmless but untidy, so consider removing `+a`.
- SPF also includes 162.246.59.205 (the cPanel server). Keep it if that server still sends mail, e.g. WordPress mail or MailChannels.
- The TTL/SOA are on self-hosted nameservers, so the edits are made in the oneinterweb WHM zone editor (or move the zone to Cloudflare first).

## 9. Activity
- **Oldest post:** 2017-03-17 ("Двояка полза" and 5 others the same day).
- **Newest post:** 2025-01-30 ("Библейски уебинар: сериозно изучаване на Писанията").
- **Posts in the last 12 months (since 2025-09-25): 0.** Before that: 1 in 2025, 1 in 2024, 0 in 2021–2023, 1 in 2020, 5 in 2019, 26 in 2017.
- The newest page is /contact/ (ID 1596, about early 2025). The site is effectively dormant.

## Files
- `survey.md`: this file
- `urls.txt`: 253 sitemap URLs (decoded)
- `urls_all.tsv`: 348-row inventory (type / id / url)
- `raw/`: sitemaps, ID probe (`idprobe.txt`), object classification (`objects.json`), post metadata (`posts.json`), media HEAD results (`media_head.json`), and saved HTML of every post and page
- `.env`: credentials (mode 600; the only file containing the password)

## Appendix: existing GitHub repos (read-only check; nothing was changed)
- **oneinterweb/prelom** (private, "Колабиративна платформа на ХЦ Прелом"): not quite empty. It has one branch, `main`, with a single "Initial commit" from 2024-03-18. That commit contains only a 78-byte README.md. There are no issues or PRs.
- **oneinterweb/sider-prelom-demo** (private, "demo new website prelom"): 2 commits on `main`, both from 2026-02-28 ("Initial commit" and "git test").
  - The repo holds a **compiled build only**: index.html, main-QB4T7PQT.js (644 KB), main-BBH4KZVP.css, and README. There is no source code.
  - Tech: a React SPA (react-dom createRoot, react-router, lucide icons, Tailwind with shadcn/ui colour tokens), generated by **Sider.ai "web-coder"**. Its images are hosted on pub-cdn.sider.ai.
  - Content: a one-page Bulgarian outreach and lead-generation landing page ("Християнски Център „Прелом“ – място за честен разговор за вярата"). It has benefits, topics, a "how it works" section, an FAQ, contact info, and a popup. The signup form is a **LeadConnector/GoHighLevel form** (api.leadconnectorhq.com/widget/form/qLUeogm1941RvHJBSvdK, via link.msgsndr.com/js/form_embed.js). None of the existing WP posts are included.
  - It is deployed as the Cloudflare Worker "prelom" on the gbakalov account: https://cloudflare-workers-autoconfig-prelom.gbakalov.workers.dev (HTTP 200).
  - **Open item #1 is a PR, not an issue:** "Add Cloudflare Workers configuration", opened by cloudflare-workers-and-pages[bot] on 2026-02-28. It adds wrangler.jsonc (framework: static; deploy: `npx wrangler deploy`). The bot's comment reports a successful preview deploy. The PR has not been merged.
