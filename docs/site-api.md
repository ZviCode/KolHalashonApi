# Site API notes

Notes on the kolhalashon.com endpoints this library uses, for maintainers. They were taken from
the requests the website itself makes (Angular app, October 2026). The server can change them
without notice; when something breaks, open the site with the browser's developer tools and
compare.

## Basics

- Base URL: `https://www.kolhalashon.com/api/` (moved from `srv.kolhalashon.com` in 2025).
- Cloudflare protects `/api/`. Plain `requests` gets a 403 "Just a moment..." page; cloudscraper
  passes. Overriding `Accept` makes even cloudscraper requests get challenged.
- Every request carries `authorization-site-key: Bearer <random 7 chars of [a-z0-9]>`. The value
  is not checked; the site generates a new one per request.
- After login, requests also carry `Authorization: Bearer <JWT>`.

## Authentication

| Request | Notes |
| --- | --- |
| `POST Accounts/UserLogin/` `{"Username": "9123456", "Password": "..."}` | Returns `{User, ExtendedUser, Token}`; 400 `{"message": "Username or password is incorrect"}` on failure. The form turns a 6 digit code into `9` + code |
| `GET Accounts/CheckToken` | `{"valid": true}` |

## Search

| Request | Notes |
| --- | --- |
| `GET Search/WebSite_GetSearchItems/{text}/{userId or -1}/{langId}/4` | Autocomplete. `SearchItemType`: 2 rav, 8 book, 9/12 category (`SearchItemStrId` = CatId), 10 shiur title |
| `POST Search/WebSite_GetSearchResultsWithSession` | First page of a full text search: `{ShiurimList, SessionText}`. Ignores `FromRow` |
| `POST Search/WebSite_GetSearchResultsNextChunk` | Next pages: same body plus `SessionID` = `SessionText` and `FromRow` |
| `GET Search/WebSite_SearchRav/{text}/{langId}/{order}/{from}/{rows}/{english}` | Rav search |
| `GET HomePage/WebSite_GetPopularRavs/{langId}` | Popular ravs (same shape as rav search) |

## Listings

All shiurim listings take the same POST body:

```json
{
  "QueryType": -1, "LangID": -1, "MasechetID": -1, "DafNo": -1, "MasechetIDY": -1, "DafNoY": -1,
  "MoedID": -1, "ParashaID": -1, "EnglishDisplay": false, "MasechetIDYOz": -1, "DafNoYOz": -1,
  "FromRow": 0, "NumOfRows": 24, "PrefferedLanguage": -1, "SearchOrder": 7, "FiltersArray": [],
  "GeneralID": 7, "CustomBool": false, "FilterSwitch": "111...", "activefilterType": "all"
}
```

| Request | `GeneralID` | `activefilterType` |
| --- | --- | --- |
| `POST Search/WebSite_GetRavShiurim/` | rav id | `all` |
| `POST Search/WebSite_GetShiurimUnderNode` | folder id | `nodeSearch` |
| `POST Search/WebSite_GetSearchResultsWithSession` | `-1`, plus `QueryType: 0`, `CustomString: <text>`, `CustomBool: true` | `default` |

`FromRow` / `NumOfRows` page the results (500 rows per page works). `SearchOrder` values are in
`SearchOrder`. `FilterSwitch` is a string of 0/1 flags; the library sends the values the site
sends for each listing.

| Request | Notes |
| --- | --- |
| `GET Ravs/GetRavBasicProp/{ravId}/{english}/` | `{ravName, ravImageFileName}` |
| `GET Ravs/WebSite_GetRavShiurimCount/{ravId}/-1` | `{VarInt: count}` |
| `GET Ravs/GetRavMainFolders/{ravId}/{langId}` | Main folders; `langId` must be a number |
| `GET LiveShiurim/WebSite_GetLiveShiurim/{langId}/{video}/true/{count}/-1` | Live shiurim. Stream: `streaming/{LivePubApp}/{LivePubName before "@"}/playlist.m3u8`; if `LivePubName == "REDIRECT"`, `LivePubApp` is a `;` separated list of URLs |

## Shiurim and files

| Request | Notes |
| --- | --- |
| `GET TblShiurimLists/WebSite_GetShiurDetails/{fileId}` | Details |
| `GET PlayShiur/GetTblShiurimAttachmentsByFileId/{fileId}` | PDFs at `PDF/Shiurim/{folder}/{AttachmentFileName}.pdf` |
| `GET files/GetPlayToken/{fileId}/{type}` | `{src, token, mode}`; `src` is a signed CDN URL. No login. Fallback: `files/GetFileToPlay/{fileId}/{type}/{token}` |
| `GET files/checkAutorizationDownload/{fileId}/false` | Login. `{key}` |
| `GET files/GetFileDownload/{fileId}/{type}/{key}/null/false/false` | The file, with a `Content-Disposition` Hebrew file name. Works without headers once the key exists |

`type`: 1 audio, 2 video, 3 HD video.

## Static files (no API, no challenge)

`{folder}` is the first 5 digits of the file id padded to 8 digits (`895822` -> `00895`).

| File | URL |
| --- | --- |
| MP3 | `mp3/NewArchive/{folder}/{id8}.mp3` |
| Thumbnail | `imgs/VideoThumbNails/{folder}/{id8}.webp` |
| Rav image | `imgs/Ravs/{RavImageFileName}` |
| PDF attachment | `PDF/Shiurim/{folder}/{AttachmentFileName}.pdf` |
| RSS | `New/RSS/CreateRss.aspx?...`, see [RSS feeds](rss.md) |

## Site pages

| Page | URL |
| --- | --- |
| Shiur | `/he/regularSite/playShiur/{fileId}` |
| Rav | `/he/regularSite/ravs/{ravId}` |
| Folder | `/he/regularSite/treeSearch/{folderId}` |
