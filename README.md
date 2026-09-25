# Християнски Център Прелом (prelom.bg)

Статично Jekyll огледало на [prelom.bg](https://prelom.bg), тема [Minimal Mistakes](https://mademistakes.com/work/minimal-mistakes-jekyll-theme/), деплой към GitHub Pages чрез Actions.

Предварителен адрес: **https://oneinterweb.github.io/prelom/** (`baseurl: "/prelom"`).

Този URL е **404**, докато хранилището е private и Pages не е включен. Безплатният GitHub план не публикува private Pages (apostolos работи, защото е public). Направете следното:

1. **Settings → General → Change repository visibility → Public**
2. **Settings → Pages → Source = GitHub Actions**
3. Merge на PR към `main` (workflow-ът се пуска само от `main`)

## Локално пускане

Нужни са Ruby 3.2+, Bundler и (за повторна миграция) Python 3.

```bash
bundle install
bundle exec jekyll serve
```

Сайтът е на http://127.0.0.1:4000/prelom/ .

Пълна повторна миграция от публичния HTML:

```bash
python3 -m pip install -r migration/requirements.txt
python3 migration/migrate.py
bundle exec jekyll build
python3 migration/verify_urls.py
```

Подробности: [`migration/README.md`](migration/README.md).

## Как да добавите публикация

1. Създайте файл в `_posts/` с име `ГГГГ-ММ-ДД-кратък-slug.md` (датата е в часова зона Europe/Sofia).
2. Попълнете YAML front matter. За да запазите точния WordPress адрес, задайте `permalink` със същия slug (включително кирилица):

```markdown
---
title: "Заглавие на публикацията"
date: 2026-09-24 12:00:00
permalink: /заглавие-на-публикацията/
slug: заглавие-на-публикацията
author: admin
categories:
  - pouchenie
excerpt: "Кратко резюме за списъка и SEO."
---
```

3. Сложете оригиналните картинки в `wp-content/uploads/ГГГГ/ММ/`, по същата схема като стария WordPress път.
4. Commit и push към `main`. Actions прави build и публикува сайта.

Страниците живеят в `_pages/` със собствен `permalink: /slug/`.

## Превключване към домейн prelom.bg

1. В `_config.yml` сменете **само** този ред:

   ```yaml
   baseurl: ""
   ```

   По желание сменете и `url:` на `https://prelom.bg`.

2. Добавете файл `CNAME` в корена с един ред: `prelom.bg`.

   **Не** добавяйте `CNAME`, докато преглеждате сайта на `oneinterweb.github.io/prelom/`.

3. Насочете apex `prelom.bg` към GitHub Pages (A записи към [IP-тата на GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)). Запазете MX, SPF, DMARC, DKIM и google-site-verification.
4. В GitHub: **Settings → Pages → Source = GitHub Actions** (не „Deploy from a branch“). Репозиторият трябва да е **public** за безплатен GitHub Pages план.

## Премахнати / заменени функции

| WordPress | Тук |
|---|---|
| Коментари | Премахнати, без заместител |
| Jetpack контактна форма (`/contact/`) | Статична HTML форма към **Formspree** (`formspree_endpoint` в `_config.yml`) |
| Търсене `?s=` | Lunr търсене на [`/search/`](/search/) |
| Мъртви PTA / MC4WP / Jetpack shortcodes | Премахнати; празните страници пренасочват към `/contact/` |
| deal.ai чат уиджет | Пропуснат |
| YouTube, Rumble, Vimeo, Facebook, sermon.net, Adobe Spark, Typeform | Запазени като iframe |
| PayPal (`/donate/`) и Mailchimp (`/newsletter/`) | Статични форми |
| Начална CRM форма | `threefold.life/crm/form/generate.js?id=36` |
| `/category/<slug>/` и `/tag/<slug>/` | Статични архиви |

## Какво трябва да направи собственикът

1. **Settings → Pages → Source: GitHub Actions.**
2. Направете хранилището **public** (безплатният план не публикува private Pages).
3. Създайте Formspree форма и сменете `formspree_endpoint` в `_config.yml`.
4. PayPal на `/donate/` използва hosted button `DXW5MGAQ43QSJ` от живата WP форма (`paypal_hosted_button_id` в `_config.yml`).
5. Когато сте готови за домейн: едната промяна на `baseurl`, файл `CNAME`, DNS (виж по-горе).

## Лиценз на съдържанието

Текстът и медията принадлежат на Християнски център Прелом. Темата Minimal Mistakes е MIT.
