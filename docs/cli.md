# Command line

Installing the package adds a `kolhalashon` command (or run `uv run kolhalashon` in a checkout).

```
kolhalashon [--json] [--env] <command> ...
```

| Global option | Meaning |
| --- | --- |
| `--json` | Print JSON instead of tab separated text |
| `--env` | Load credentials from `.env` / the environment and cache the login token |

## Commands

| Command | Description |
| --- | --- |
| `items TEXT` | Autocomplete search (ravs, categories, titles) |
| `search TEXT [-n LIMIT]` | Full text shiurim search |
| `ravs TEXT [-n LIMIT]` | Search ravs by name |
| `popular` | Popular ravs |
| `rav RAV_ID [-n LIMIT]` | Shiurim of a rav |
| `folders RAV_ID` | Main folders of a rav |
| `folder FOLDER_ID [-n LIMIT]` | Shiurim in a folder |
| `details FILE_ID` | Details of a shiur |
| `url FILE_ID [-q audio\|video\|hd]` | Streaming URL |
| `live [-n LIMIT]` | Live shiurim and their `.m3u8` URLs |
| `attachments FILE_ID [-o DIR]` | List PDF attachments, or download them into `DIR` |
| `rss FOLDER_ID [--rav ID] [--oldest] [--page N] [--load]` | Print a folder's feed URL, or load and list it |
| `rss --shiur FILE_ID [--load]` | Same, for the folder of a shiur |
| `download FILE_ID [-q Q] [-o DIR] [--server-name]` | Download one shiur (login) |
| `download-folder FOLDER_ID [-q Q] [-o DIR] [-n LIMIT] [-t TEMPLATE] [--attachments]` | Download a folder (login) |
| `download-rav RAV_ID [...]` | Download every shiur of a rav (login), same options |

Text output columns are tab separated, so they work with `cut`, `sort` and spreadsheets.

## Examples

```bash
kolhalashon ravs "וייס"
kolhalashon folders 7
kolhalashon rss 5761 --rav 7
kolhalashon rss --shiur 42863638 --load
kolhalashon --json details 42863638
kolhalashon live
kolhalashon --env download 42863638 -o downloads --server-name
kolhalashon --env download-folder 5761 -o downloads -t "{date} {title}" --attachments
```

The exit code is `1` when the library raises an error, with the message on stderr.
