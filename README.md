# Kol Halashon API

Typed Python wrapper for the [Kol Halashon](https://www.kolhalashon.com/he/regularSite/home) website API.

ספריית פייתון לעבודה מול האתר של קול הלשון: חיפוש שיעורים ורבנים, רשימות שיעורים של רב או של תיקייה, פרטי שיעור, קישורי האזנה, הורדה (עם חשבון), וכתובות RSS לכל תיקייה, כולל טעינה וניתוח של הפיד.

Full documentation: [docs/](docs/README.md) ([API reference](docs/api-reference.md), [RSS](docs/rss.md), [downloads](docs/downloads.md), [CLI](docs/cli.md), [מדריך בעברית](docs/guide-he.md)).

## Installation

```bash
pip install kolhalashon            # or: uv add kolhalashon
pip install "kolhalashon[dotenv]"  # also load credentials from a .env file
```

Python 3.10+.

## Quick start

```python
from kolhalashon import KolHalashonAPI, QualityLevel

api = KolHalashonAPI()

# Autocomplete search: ravs, categories, shiur titles
result = api.search_items("אשר וייס")
rav = result.rabanim[0]
print(rav.id, rav.name)  # 7 וייס, הרב אשר

# Full text search, a rav's shiurim, a folder's shiurim
shiurim = api.search_shiurim("אשר וייס", limit=10)
for shiur in api.iter_rav_shiurim(7, limit=50):
    print(shiur.file_id, shiur.title, shiur.duration_seconds)
folders = api.get_rav_folders(7)
shiurim = list(api.iter_folder_shiurim(folders[0].folder_id))

# A single shiur
details = api.get_shiur_details(42863638)
print(api.get_play_url(details.file_id, QualityLevel.VIDEO))  # streaming URL, no login needed
print(details.audio_url)  # public MP3 URL
```

All results are typed dataclasses (`Shiur`, `ShiurDetails`, `Folder`, `Rav`, `SearchItem`,
`RssFeed`, ...). The original JSON is kept in `.raw`.

## Ravs, live shiurim and attachments

```python
ravs = api.search_ravs("וייס", limit=10)  # Rav: rav_id, name, shiurim_count, image_url...
popular = api.get_popular_ravs()

for live in api.get_live_shiurim():
    print(live.rav, live.main_topic, live.stream_url)  # HLS .m3u8 URL

for attachment in api.get_attachments(42863638):  # PDF sources of a shiur
    print(attachment.title, attachment.url)
    api.download_attachment(attachment, "pdfs")
```

## RSS

Every folder (series) has a podcast style RSS feed. The site no longer shows a button for it, but
the feeds still work. Each page holds up to 100 items.

```python
from kolhalashon import KolHalashonAPI, RssOrder

api = KolHalashonAPI()

url = api.get_rss_url(5761, rav_id=7)  # build the URL, no network
url = api.get_rss_url(5761, 7, order=RssOrder.OLDEST, page=2)
url = api.get_shiur_rss_url(42863638)  # the feed of the folder of a shiur

feed = api.load_rss(5761, rav_id=7)  # or api.load_rss(url)
for item in feed:
    print(item.published, item.file_id, item.title, item.url)

for page in api.iter_rss(5761, 7):  # every page of a long feed
    ...
```

`build_rss_url` and `parse_rss` are also available as standalone functions.

## Login and downloads

Downloading through the site's download button needs an account. Pass the credentials directly,
or put them in the environment / `.env` (see `.env.example`):

```python
api = KolHalashonAPI(username="123456", password="...", use_session=True)
# or
api = KolHalashonAPI.from_env()  # KOL_HALASHON_USERNAME / KOL_HALASHON_PASSWORD

path = api.download_file(
    42863638,
    QualityLevel.AUDIO,
    "downloads",
    use_server_filename=True,  # Hebrew title from the server
    progress=lambda done, total: ...,
)
```

The user code is converted like the site's login form does it (a 6 digit code gets a leading
`9`). With `use_session=True` the login token is cached in `kolhalashon_session.json` (file mode
600) and reused until it expires.

## Bulk downloads

Download a whole folder or every shiur of a rav. Existing files are skipped, so an interrupted
run can be resumed, and errors are collected instead of stopping the run.

```python
results = api.download_folder(
    5761,
    "downloads/weiss",
    filename_template="{date} {title}",  # fields: file_id title rav rav_id folder_id date quality
    with_attachments=True,
    on_result=lambda r: print(r.shiur.file_id, "skip" if r.skipped else r.error or "ok"),
)
failed = [r for r in results if not r.ok]

api.download_rav(7, "downloads/rav-7", QualityLevel.AUDIO, limit=100)
api.download_shiurim(api.search_shiurim("הלכות שבת", limit=20), "downloads/shabbat")
```

## Command line

```bash
kolhalashon items "אשר וייס"
kolhalashon search "הלכות שבת" -n 10
kolhalashon rav 7 -n 20
kolhalashon folders 7
kolhalashon folder 5761
kolhalashon details 42863638 --json
kolhalashon url 42863638 -q hd
kolhalashon rss 5761 --rav 7            # print the URL
kolhalashon rss --shiur 42863638 --load # load and list the feed
kolhalashon --env download 42863638 -o downloads --server-name
kolhalashon ravs "וייס"
kolhalashon popular
kolhalashon live
kolhalashon attachments 42863638 -o pdfs
kolhalashon --env download-folder 5761 -o downloads -t "{date} {title}" --attachments
kolhalashon --env download-rav 7 -o downloads -n 50
```

## Cloudflare

The JSON API (`/api/...`) sits behind a Cloudflare challenge. By default the client uses a
[cloudscraper](https://pypi.org/project/cloudscraper/) session (`kolhalashon.api.create_session()`),
which passes it. If a request is still challenged, `CloudflareChallengeError` is raised instead of
returning HTML. Requests that fail with a connection error or 429/5xx are retried 3 times with backoff
(`KolHalashonAPI(retries=...)`). You can pass your own session (`KolHalashonAPI(session=...)`)
for proxies or headers; do not override the `Accept` header, Cloudflare challenges requests that do.

## Migrating from 1.x

- The API moved from `srv.kolhalashon.com` to `www.kolhalashon.com/api/`.
- `search_items()` returns `SearchItem` objects (`item.id`, `item.name`); `item["ID"]` and
  `item["NameHebrew"]` still work. Categories now have their own `categories` group.
- `Shiur` / `ShiurDetails` have more fields and are keyword only.
- The session is stored as JSON instead of pickle, and no `print()` / `logging.basicConfig()`
  calls are made by the library.
- `python-dotenv` is optional (`kolhalashon[dotenv]`) and `.env` is only loaded by `from_env()`.
- `get_all_rav_shiurim()` still exists; `iter_rav_shiurim()` streams the results instead.

## Development

```bash
uv sync
uv run pytest            # offline tests
uv run pytest -m live    # against the real site
uv run ruff check && uv run ruff format --check
uv run mypy
```
