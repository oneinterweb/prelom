# Миграция от WordPress (prelom.bg)

Скриптовете тук пресъздават съдържанието на https://prelom.bg от **публичния HTML**. REST API, xmlrpc и wp-login са блокирани от WP Cerber. Cloudflare предизвиква datacenter IP-та, затова HTML се чете през [Jina Reader](https://r.jina.ai/), а картинките се свалят през `wsrv.nl`.

## Какво правят

| Скрипт | Роля |
|---|---|
| `migrate.py` | Сваля постове, страници и категории; пише Markdown; сваля медия; прави отчет |
| `verify_urls.py` | Сравнява `urls_all.tsv` с `_site/` след `jekyll build` |
| `check_links.py` | Търси счупени вътрешни линкове и картинки в `_site/` |

## Стартиране

```bash
python3 -m pip install -r migration/requirements.txt
python3 migration/migrate.py
bundle exec jekyll build
python3 migration/verify_urls.py
python3 migration/check_links.py
```

Само конверсия от вече сваления HTML в `migration/raw/html/`:

```bash
python3 migration/convert_html.py
# или
python3 migration/migrate.py --from-html
```
