# API reference

Everything below is importable from the top level package:

```python
from kolhalashon import KolHalashonAPI, QualityLevel, SearchOrder, Shiur, ...
```

"Login" marks methods that need an account. All other methods work anonymously.

## `KolHalashonAPI`

See [Getting started](getting-started.md#configuration) for the constructor arguments.

### Session

| Method | Returns | Notes |
| --- | --- | --- |
| `KolHalashonAPI.from_env(dotenv_path=None, **kwargs)` | `KolHalashonAPI` | Loads `.env` (if python-dotenv is installed), `use_session=True` by default |
| `login(username=None, password=None)` | `bool` | Raises `AuthenticationError` with the server's message on failure |
| `logout()` | `None` | Forgets the token and deletes the session file |
| `check_token()` | `bool` | Asks the server whether the token is still valid |
| `is_logged_in` | `bool` | Property; checks the token expiry locally |
| `session` | `requests.Session` | Property; the HTTP session in use |

### Search

| Method | Returns |
| --- | --- |
| `search_items(keyword)` | `Category`: autocomplete results grouped into `rabanim`, `books`, `shiurim`, `categories`, `others` |
| `search_shiurim(text, *, limit=24, page_size=100, order=SearchOrder.NEWEST, language=None)` | `list[Shiur]`; `limit=None` for all results |
| `iter_search_shiurim(text, *, limit=None, ...)` | `Iterator[Shiur]`, fetched page by page |
| `search_ravs(text, *, limit=24, offset=0, language=Language.HEBREW)` | `list[Rav]` |

### Ravs

| Method | Returns |
| --- | --- |
| `get_rav(rav_id)` | `Rav` with name, image and shiurim count |
| `get_popular_ravs(language=Language.HEBREW)` | `list[Rav]` |
| `get_rav_folders(rav_id, language=Language.HEBREW)` | `list[Folder]`: the rav's main folders (series) |
| `search_rav_shiurim(rav_id, from_row=0, num_rows=24, *, order, language)` | `list[Shiur]`: one page |
| `iter_rav_shiurim(rav_id, *, limit=None, page_size=100, order, language)` | `Iterator[Shiur]` over all pages |
| `get_all_rav_shiurim(rav_id, page_size=100)` | `list[Shiur]`: every shiur (can be thousands) |

### Folders

| Method | Returns |
| --- | --- |
| `get_folder_shiurim(folder_id, from_row=0, num_rows=24, *, order, language)` | `list[Shiur]`: one page, including sub folders |
| `iter_folder_shiurim(folder_id, *, limit=None, page_size=100, order, language)` | `Iterator[Shiur]` |

### Shiurim and media

| Method | Returns |
| --- | --- |
| `get_shiur_details(file_id)` | `ShiurDetails`; raises `ShiurDetailsNotFoundException` |
| `get_play_source(file_id, quality=QualityLevel.AUDIO)` | `PlaySource`: streaming URL plus fallback |
| `get_play_url(file_id, quality=QualityLevel.AUDIO)` | `str`: streaming URL used by the site's player |
| `get_audio_url(file_id)` | `str`: public MP3 URL, no request made |
| `get_attachments(file_id)` | `list[Attachment]`: PDF sources of a shiur |
| `get_live_shiurim(count=20, *, language=Language.HEBREW, video=True)` | `list[LiveShiur]`: current broadcasts with HLS URLs |

### RSS

See [RSS feeds](rss.md).

| Method | Returns |
| --- | --- |
| `get_rss_url(folder_id, rav_id=None, *, audio_only=True, order=RssOrder.NEWEST, page=1, language=Language.HEBREW)` | `str`, no request made |
| `get_shiur_rss_url(file_id, **kwargs)` | `str`: feed of the folder a shiur belongs to |
| `load_rss(url_or_folder_id, **kwargs)` | `RssFeed` |
| `iter_rss(folder_id, rav_id=None, **kwargs)` | `Iterator[RssFeed]`: one feed per page of 100 items |

### Downloads

See [Downloads](downloads.md).

| Method | Returns |
| --- | --- |
| `download_file(file_id, quality_level=AUDIO, dest=".", *, filename=None, use_server_filename=False, overwrite=True, progress=None)` | `str` path. Login |
| `download_shiurim(shiurim, dest=".", quality_level=AUDIO, *, filename_template, skip_existing=True, with_attachments=False, on_result=None)` | `list[DownloadResult]`. Login |
| `download_folder(folder_id, dest=".", quality_level=AUDIO, *, limit=None, order=SearchOrder.OLDEST, **kwargs)` | `list[DownloadResult]`. Login |
| `download_rav(rav_id, dest=".", quality_level=AUDIO, *, limit=None, order=SearchOrder.OLDEST, **kwargs)` | `list[DownloadResult]`. Login |
| `download_attachment(attachment, dest=".", *, filename=None, overwrite=True)` | `str` path |
| `get_download_url(file_id, quality_level=AUDIO)` | `str`: signed URL, usable without headers. Login |
| `get_download_key(file_id)` | `str`. Login |

## Module functions

| Function | Description |
| --- | --- |
| `create_session(retries=3)` | The default cloudscraper session with retries |
| `normalize_username(code)` | User code conversion used by `login()` |
| `build_rss_url(...)` | Same as `KolHalashonAPI.get_rss_url` |
| `parse_rss(content, url="")` | Parse feed XML into an `RssFeed` |
| `format_shiur_filename(shiur, template, quality=None)` | Fill a file name template |
| `sanitize_filename(name, max_length=180)` | Make a string safe as a file name |

## Models

All models are dataclasses. Models built from API data keep the original JSON in `.raw`.

### `Shiur`

| Field | Type | Notes |
| --- | --- | --- |
| `file_id` | `int` | |
| `title`, `title_english` | `str` | |
| `rav`, `rav_english`, `rav_id`, `rav_image` | | |
| `duration` | `str` | `HH:MM:SS`; `duration_seconds` property |
| `record_date` | `str` | ISO string; `record_datetime` property |
| `main_topic`, `main_topic_english` | `str` | |
| `category_1`, `category_2`, `category_id_1`, `category_id_2` | | |
| `folder_id`, `language_id` | `int \| None` | |
| `audio_available`, `video_available`, `hd_video_available` | `bool` | `available_qualities` property |
| `download_count`, `women_only`, `shiur_type`, `viewed_by_user` | | |
| `is_locked`, `download_disabled` | `bool` | |

Properties: `audio_url`, `thumbnail_url`, `page_url`.

`ShiurDetails` adds `categories: list[str]`. `LiveShiur` adds `stream_urls: list[str]` and the
`stream_url` property.

### Other models

| Model | Fields |
| --- | --- |
| `Rav` | `rav_id`, `name`, `name_english`, `image_file_name`, `shiurim_count`, `download_count`, `last_record_date`, `alternative_names`; properties `image_url`, `page_url` |
| `Folder` | `folder_id`, `rav_id`, `title`, `title_english`, `category_id`, `language_id`, `has_audio`, `has_video`, `order`, `created`, `modified`; property `page_url` |
| `SearchItem` | `type`, `id`, `big_id`, `str_id`, `name`, `name_english`; property `item_type`. `item["ID"]` / `item["NameHebrew"]` work for 1.x compatibility |
| `Category` | Lists `rabanim`, `books`, `shiurim`, `categories`, `others`; iterable, `len()` |
| `Attachment` | `attachment_id`, `file_id`, `title`, `file_name`, `order`; property `url` |
| `PlaySource` | `file_id`, `quality`, `url`, `fallback_url`, `mode` |
| `RssFeed` | `url`, `title`, `link`, `description`, `image_url`, `language`, `items`; iterable, `len()` |
| `RssItem` | `title`, `url`, `published`, `length`, `mime_type`; property `file_id` |
| `DownloadResult` | `shiur`, `path`, `skipped`, `error`; property `ok` |

## Enums

| Enum | Values |
| --- | --- |
| `QualityLevel` | `AUDIO=1`, `VIDEO=2`, `HD_VIDEO=3` (`extension`, `label` properties) |
| `SearchOrder` | `RELEVANCE=1`, `RAV_NAME_ASC=2`, `RAV_NAME_DESC=3`, `TITLE_ASC=4`, `TITLE_DESC=5`, `DURATION=6`, `NEWEST=7`, `OLDEST=8`, `FOLDER_ORDER=9` |
| `Language` | `ALL=-1`, `HEBREW=1`, `ENGLISH=2` |
| `RssOrder` | `NEWEST=1`, `OLDEST=2` |
| `SearchItemType` | `RAV=2`, `BOOK=8`, `CATEGORY=9`, `SHIUR=10`, `CATEGORY_ALIAS=12` |

## Exceptions

```
KolHalashonError
├── APIError                        (.status_code, .url)
│   ├── CloudflareChallengeError
│   ├── SearchFailedException
│   ├── ShiurDetailsNotFoundException
│   ├── DownloadKeyNotFoundException
│   └── DownloadFailedException     (.file_id, .quality_level)
├── AuthenticationError
│   └── TokenExpiredException
├── SessionDisabledException        (an action needs login and no credentials are set)
├── SessionNotLoadedException
└── RssError
```

Catch `KolHalashonError` to handle every error raised by the library.
