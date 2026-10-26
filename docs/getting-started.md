# Getting started

## Install

```bash
pip install kolhalashon            # or: uv add kolhalashon
pip install "kolhalashon[dotenv]"  # to load credentials from a .env file
```

Requires Python 3.10 or newer.

## First requests

Most features need no account:

```python
from kolhalashon import KolHalashonAPI

api = KolHalashonAPI()

result = api.search_items("אשר וייס")  # autocomplete: ravs, categories, titles
rav = result.rabanim[0]

for shiur in api.iter_rav_shiurim(rav.id, limit=20):
    print(shiur.file_id, shiur.record_date[:10], shiur.title)
```

Ids you will meet:

| Id | Where it comes from | Used by |
| --- | --- | --- |
| `rav_id` | `search_items().rabanim[i].id`, `search_ravs()`, `Shiur.rav_id` | rav listings, folders, `download_rav` |
| `folder_id` | `get_rav_folders()`, `Shiur.folder_id` | folder listings, RSS, `download_folder` |
| `file_id` | any `Shiur`, the `playShiur/<id>` part of a site URL | details, playback, downloads, attachments |

## Login

Downloading through the official download endpoint needs an account. Everything else works
anonymously.

```python
api = KolHalashonAPI(username="123456", password="...", use_session=True)
```

or, with `KOL_HALASHON_USERNAME` / `KOL_HALASHON_PASSWORD` in the environment or a `.env` file:

```python
api = KolHalashonAPI.from_env()
```

- The user code is converted like the site's login form does it: a 6 digit code gets a leading
  `9` (`123456` -> `9123456`), `*12345` becomes `912345`.
- With `use_session=True` the token is saved to `kolhalashon_session.json` (readable by the owner
  only) and reused until it expires, so later runs do not log in again.
- `api.login()` can also be called at any time; `api.logout()` forgets the token and deletes the
  file.

## Configuration

`KolHalashonAPI(...)` keyword arguments:

| Argument | Default | Meaning |
| --- | --- | --- |
| `username`, `password` | environment variables | Account credentials |
| `use_session` | `False` | Log in on creation and cache the token |
| `session_file` | `"kolhalashon_session.json"` | Where the token is cached (`None` to disable) |
| `session` | `create_session()` | Your own `requests.Session` |
| `timeout` | `30` | Seconds per request |
| `language` | `Language.ALL` | Preferred shiurim language for listings |
| `retries` | `3` | Retries on connection errors and 429/5xx (default session only) |

## Cloudflare

The JSON API is behind a Cloudflare challenge. The default session is a
[cloudscraper](https://pypi.org/project/cloudscraper/) session, which passes it. If a request is
still challenged, `CloudflareChallengeError` is raised. When passing your own session, do not
override the `Accept` header: Cloudflare challenges requests that do.

## Logging

The library logs through the standard `logging` module (loggers under `kolhalashon`) and never
configures logging itself:

```python
import logging

logging.basicConfig(level=logging.DEBUG)  # shows every request
```
