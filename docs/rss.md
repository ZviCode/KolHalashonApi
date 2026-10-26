# RSS feeds

Every folder (series) on Kol Halashon has a podcast style RSS feed. The new site no longer shows
a button for it, but the legacy endpoint still serves the feeds:

```
https://www.kolhalashon.com/New/RSS/CreateRss.aspx?Lang=Hebrew&FID=5761&AudioOnly=True&RavID=7&Order=1&IsEdge=True&PageNum=1&LangID=1
```

Feeds are public: no login and no Cloudflare challenge. Podcast apps can subscribe to them
directly.

## Parameters

| Parameter | Library argument | Meaning |
| --- | --- | --- |
| `FID` | `folder_id` | Folder id (required) |
| `RavID` | `rav_id` | Rav id; optional for the server, part of the URLs the site used to publish |
| `Order` | `order` | `RssOrder.NEWEST` (1) or `RssOrder.OLDEST` (2) |
| `PageNum` | `page` | 1-based page, 100 items per page; a page past the end has no items |
| `Lang` / `LangID` | `language` | Hebrew or English channel texts |
| `AudioOnly` | `audio_only` | Sent like the site did; the server currently returns MP3 items either way |
| `IsEdge` | (fixed `True`) | Sent like the site did |

## Getting a feed URL

```python
from kolhalashon import KolHalashonAPI, RssOrder, build_rss_url

api = KolHalashonAPI()

api.get_rss_url(5761, rav_id=7)  # no request made
api.get_rss_url(5761, 7, order=RssOrder.OLDEST, page=2)
build_rss_url(5761, 7)  # same, without a client

api.get_shiur_rss_url(42863638)  # feed of the folder of a shiur

for folder in api.get_rav_folders(7):  # feeds of every folder of a rav
    print(folder.title, api.get_rss_url(folder.folder_id, 7))
```

## Loading a feed

```python
feed = api.load_rss(5761, rav_id=7)  # folder id + URL arguments
feed = api.load_rss(url)  # or any feed URL

print(feed.title, feed.image_url, len(feed))
for item in feed:
    print(item.published, item.file_id, item.title, item.url, item.length)
```

`item.file_id` is parsed from the enclosure URL, so it can be passed to `get_shiur_details`,
`get_attachments` or `download_file`.

## Long feeds

`iter_rss` yields one `RssFeed` per page until a page has fewer than 100 items:

```python
items = [item for page in api.iter_rss(5761, 7) for item in page]
```

## Parsing saved XML

```python
from kolhalashon import parse_rss

feed = parse_rss(open("feed.xml", "rb").read())
```

Invalid XML or a document without `<channel>` raises `RssError`.
