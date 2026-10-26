# Downloads

## Without an account

These URLs work without logging in:

| What | How |
| --- | --- |
| Streaming URL of any quality (what the site's player uses) | `api.get_play_url(file_id, QualityLevel.VIDEO)` |
| Public MP3 URL (the one RSS feeds link to) | `api.get_audio_url(file_id)` or `shiur.audio_url` |
| PDF attachments | `api.get_attachments(file_id)`, `api.download_attachment(attachment, dest)` |

## Single shiur (login)

```python
from kolhalashon import KolHalashonAPI, QualityLevel

api = KolHalashonAPI.from_env()

path = api.download_file(
    42863638,
    QualityLevel.AUDIO,  # AUDIO -> .mp3, VIDEO / HD_VIDEO -> .mp4
    "downloads",  # created if missing
    use_server_filename=True,  # "<title> - <rav> - <id>.mp3" in Hebrew, as the server names it
    progress=lambda done, total: print(done, total),
)
```

- Without `filename` / `use_server_filename` the file is called `shiur_<id>_<quality>.<ext>`.
- Data is written to `<name>.part` and renamed when complete, so a crash never leaves a file that
  looks finished.
- `overwrite=False` keeps an existing file.
- `get_download_url()` returns the signed URL instead, for use with another downloader.

## Bulk downloads (login)

```python
results = api.download_folder(
    5761,
    "downloads/weiss",
    QualityLevel.AUDIO,
    filename_template="{date} {title}",
    with_attachments=True,
    on_result=lambda r: print(r.shiur.file_id, "skip" if r.skipped else r.error or "ok"),
)
```

| Method | Shiurim |
| --- | --- |
| `download_folder(folder_id, dest, quality, *, limit=None, order=SearchOrder.OLDEST, **options)` | A folder, including sub folders |
| `download_rav(rav_id, dest, quality, *, limit=None, order=SearchOrder.OLDEST, **options)` | Every shiur of a rav |
| `download_shiurim(shiurim, dest, quality, **options)` | Any iterable of `Shiur`, e.g. search results |

Options:

| Option | Default | Meaning |
| --- | --- | --- |
| `filename_template` | `"{title} - {rav} - {file_id}"` | File name without extension |
| `skip_existing` | `True` | Skip files already in `dest`; rerunning resumes an interrupted run |
| `with_attachments` | `False` | Also save each shiur's PDFs as `<name> - <pdf title>.pdf` |
| `on_result` | `None` | Called with each `DownloadResult` as it finishes |

Errors for single shiurim (missing quality, server errors) are stored in `DownloadResult.error`
and the run continues. Login errors stop the run.

### File name templates

Fields available to `filename_template`:

| Field | Example |
| --- | --- |
| `{file_id}` | `42863638` |
| `{title}` | `פרשת לך לך - מצוות ישוב ארץ ישראל` |
| `{rav}` | `הרב אשר וייס` |
| `{rav_id}` | `7` |
| `{folder_id}` | `5761` |
| `{date}` | `2026-10-22` |
| `{quality}` | `audio`, `video` or `hd` |

The result goes through `sanitize_filename`: characters invalid on Windows are removed, `"`
becomes `''` (so `זצ"ל` stays readable) and long names are cut to 180 characters. Templates can
include sub folders only by changing `dest`, since `/` is removed.

Ordering by date in a file manager works best with `{date}` first, as suggested in the forum
thread:

```python
api.download_rav(7, "downloads/rav-7", filename_template="{date} {title}")
```
