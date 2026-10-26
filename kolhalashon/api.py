from __future__ import annotations

import contextlib
import logging
import os
import random
import re
import string
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote, unquote

import cloudscraper  # type: ignore[import-untyped]
import requests
from urllib3.util.retry import Retry

from .models.enums import Language, QualityLevel, RssOrder, SearchItemType, SearchOrder
from .models.exceptions import (
    APIError,
    AuthenticationError,
    CloudflareChallengeError,
    DownloadFailedException,
    DownloadKeyNotFoundException,
    KolHalashonError,
    RssError,
    SearchFailedException,
    SessionDisabledException,
    ShiurDetailsNotFoundException,
)
from .models.raw import (
    RawAttachment,
    RawFolder,
    RawLiveShiur,
    RawLoginResponse,
    RawPlayToken,
    RawRavBasicProp,
    RawRavSearchResult,
    RawSearchItem,
    RawSearchResults,
    RawShiur,
)
from .models.shiur import (
    Attachment,
    Category,
    DownloadResult,
    Folder,
    LiveShiur,
    PlaySource,
    Rav,
    SearchItem,
    Shiur,
    ShiurDetails,
)
from .rss import RSS_PAGE_SIZE, RssFeed, build_rss_url, parse_rss
from .utils import urls
from .utils.filenames import sanitize_filename
from .utils.session_manager import SessionManager

logger = logging.getLogger(__name__)

USERNAME_ENV = "KOL_HALASHON_USERNAME"
PASSWORD_ENV = "KOL_HALASHON_PASSWORD"

# No "accept" override: Cloudflare challenges cloudscraper requests that change it.
DEFAULT_HEADERS = {
    "accept-language": "he-IL,he;q=0.9,en;q=0.8",
    "origin": urls.BASE_URL.rstrip("/"),
    "referer": urls.BASE_URL,
}
# Only used for plain sessions; cloudscraper picks a user agent matching its TLS setup.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# `FilterSwitch` values the website sends for each kind of listing.
_FILTERS_ALL = "1" * 99
_FILTERS_SEARCH = "1111111011000101100100000000000010" + "0" * 65
_FILTERS_NODE = "1111111011000001101101001000000010" + "0" * 65

_RETRY_STATUSES = (429, 500, 502, 503, 504)
DEFAULT_FILENAME_TEMPLATE = "{title} - {rav} - {file_id}"

_SITE_KEY_ALPHABET = string.ascii_lowercase + string.digits
_FILENAME_STAR = re.compile(r"filename\*=UTF-8''([^;]+)", re.IGNORECASE)

ProgressCallback = Callable[[int, int | None], None]


def create_session(retries: int = 3) -> requests.Session:
    """Default HTTP session: a cloudscraper session, which passes the Cloudflare challenge.

    Failed connections and 429/5xx answers are retried ``retries`` times with backoff.
    """
    session: requests.Session = cloudscraper.create_scraper()
    if retries:
        # Keep cloudscraper's own adapter (it carries the TLS setup); only add retries.
        adapter = session.get_adapter(urls.BASE_URL)
        adapter.max_retries = Retry(  # type: ignore[attr-defined]
            total=retries,
            backoff_factor=1,
            status_forcelist=_RETRY_STATUSES,
            allowed_methods=None,
            raise_on_status=False,
        )
    return session


def _site_key() -> str:
    # The website sends a random 7 character key with every request.
    return "Bearer " + "".join(random.choices(_SITE_KEY_ALPHABET, k=7))


def normalize_username(username: str | int) -> int:
    """Convert a user code the way the website's login form does.

    6 digit codes get a leading ``9``; ``*12345`` / ``#12345`` become ``912345``.
    """
    value = str(username).strip()
    if re.fullmatch(r"[0-9]{6}", value):
        value = "9" + value
    elif re.fullmatch(r"[*#][0-9]{5}", value):
        value = "9" + value[1:]
    elif re.fullmatch(r"[*#][0-9]{4}", value):
        value = value[1:]
    try:
        return int(value)
    except ValueError as exc:
        raise AuthenticationError(f"Invalid user code: {username!r}") from exc


def _is_cloudflare_challenge(response: requests.Response) -> bool:
    if response.status_code not in (403, 429, 503):
        return False
    if response.headers.get("cf-mitigated") == "challenge":
        return True
    content_type = response.headers.get("content-type", "")
    return "text/html" in content_type and "Just a moment" in response.text[:2000]


def format_shiur_filename(
    shiur: Shiur, template: str = DEFAULT_FILENAME_TEMPLATE, quality: QualityLevel | None = None
) -> str:
    """Fill a file name template with the fields of a shiur (not sanitized)."""
    record = shiur.record_datetime
    return template.format(
        file_id=shiur.file_id,
        title=shiur.title or shiur.title_english or str(shiur.file_id),
        rav=shiur.rav or shiur.rav_english,
        rav_id=shiur.rav_id or "",
        folder_id=shiur.folder_id or "",
        date=record.date().isoformat() if record else "",
        quality=quality.label if quality else "",
    )


def _save_response(
    response: requests.Response,
    target: Path,
    progress: ProgressCallback | None,
    chunk_size: int,
) -> None:
    """Stream a response into ``target`` through a ``.part`` file."""
    total = (
        int(response.headers["content-length"]) if "content-length" in response.headers else None
    )
    done = 0
    partial = target.with_name(target.name + ".part")
    try:
        with response, partial.open("wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                file.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(target)


class KolHalashonAPI:
    """Client for the kolhalashon.com website API.

    Anonymous use covers search, listings, details, streaming URLs and RSS.
    Downloads through the official download endpoint need a logged in account.
    """

    BASE_URL = urls.BASE_URL
    API_URL = urls.API_URL

    def __init__(
        self,
        username: str | int | None = None,
        password: str | None = None,
        *,
        use_session: bool = False,
        session_file: str | os.PathLike[str] | None = "kolhalashon_session.json",
        session: requests.Session | None = None,
        timeout: float = 30,
        language: Language = Language.ALL,
        retries: int = 3,
    ) -> None:
        """
        :param username: user code; defaults to ``$KOL_HALASHON_USERNAME``.
        :param password: password; defaults to ``$KOL_HALASHON_PASSWORD``.
        :param use_session: log in on creation and cache the token in ``session_file``.
        :param session: custom ``requests.Session``; defaults to :func:`create_session`.
        :param language: preferred shiurim language for listings.
        :param retries: retries for failed requests of the default session.
        """
        self.username = username if username is not None else os.getenv(USERNAME_ENV, "")
        self.password = password if password is not None else os.getenv(PASSWORD_ENV, "")
        self.use_session = use_session
        self.timeout = timeout
        self.language = language
        self.session_manager = SessionManager(
            session_file if use_session else None, session or create_session(retries)
        )
        self.session.headers.update(DEFAULT_HEADERS)
        if str(self.session.headers.get("user-agent", "")).startswith("python-requests"):
            self.session.headers["user-agent"] = BROWSER_USER_AGENT

        if self.use_session:
            self._init_session()

    @classmethod
    def from_env(
        cls, dotenv_path: str | os.PathLike[str] | None = None, **kwargs: Any
    ) -> KolHalashonAPI:
        """Create a client from environment variables.

        Loads ``.env`` first when python-dotenv is installed (``kolhalashon[dotenv]``).
        """
        try:
            from dotenv import load_dotenv
        except ImportError:
            logger.debug("python-dotenv is not installed; using the process environment only")
        else:
            load_dotenv(dotenv_path)
        kwargs.setdefault("use_session", True)
        return cls(**kwargs)

    @property
    def session(self) -> requests.Session:
        return self.session_manager.session

    @property
    def is_logged_in(self) -> bool:
        return self.session_manager.is_token_valid()

    # ------------------------------------------------------------------ HTTP

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = path if path.startswith("http") else self.API_URL + path
        headers: dict[str, str] = {"authorization-site-key": _site_key()}
        if self.session_manager.auth_token:
            headers["authorization"] = f"Bearer {self.session_manager.auth_token}"
        headers.update(kwargs.pop("headers", None) or {})
        kwargs.setdefault("timeout", self.timeout)
        logger.debug("%s %s", method, url)
        response = self.session.request(method, url, headers=headers, **kwargs)
        if _is_cloudflare_challenge(response):
            raise CloudflareChallengeError(url, response.status_code)
        return response

    def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._request(method, path, **kwargs)
        if response.status_code != 200:
            raise APIError(
                f"{method} {path} failed: {response.text[:200]}", response.status_code, response.url
            )
        if not response.content:
            return None
        return response.json()

    def _shiurim_query(
        self,
        general_id: int,
        *,
        from_row: int,
        num_rows: int,
        order: SearchOrder,
        filter_switch: str,
        filter_type: str,
        language: Language | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {
            "QueryType": -1,
            "LangID": -1,
            "MasechetID": -1,
            "DafNo": -1,
            "MasechetIDY": -1,
            "DafNoY": -1,
            "MoedID": -1,
            "ParashaID": -1,
            "EnglishDisplay": False,
            "MasechetIDYOz": -1,
            "DafNoYOz": -1,
            "FromRow": from_row,
            "NumOfRows": num_rows,
            "PrefferedLanguage": int(language if language is not None else self.language),
            "SearchOrder": int(order),
            "FiltersArray": [],
            "GeneralID": general_id,
            "CustomBool": False,
            "FilterSwitch": filter_switch,
            "activefilterType": filter_type,
        }
        query.update(extra)
        return query

    def _post_shiurim(self, path: str, query: dict[str, Any], error: str) -> list[Shiur]:
        try:
            data = self._json("POST", path, json=query)
        except CloudflareChallengeError:
            raise
        except APIError as exc:
            raise SearchFailedException(
                f"{error}: {exc.message}", exc.status_code, exc.url
            ) from exc
        return self.format_shiurim(cast("list[RawShiur]", data or []))

    @staticmethod
    def _paginate(
        fetch: Callable[[int, int], list[Shiur]], page_size: int, limit: int | None
    ) -> Iterator[Shiur]:
        from_row = 0
        yielded = 0
        while True:
            rows = page_size if limit is None else min(page_size, limit - yielded)
            if rows <= 0:
                return
            batch = fetch(from_row, rows)
            yield from batch
            yielded += len(batch)
            if len(batch) < rows:
                return
            from_row += len(batch)

    # ----------------------------------------------------------------- login

    def _init_session(self) -> None:
        self.session_manager.load_session()
        if self.session_manager.is_token_valid():
            return
        if self.username and self.password:
            self.login(self.username, self.password)
        else:
            logger.info("No valid saved session and no credentials; continuing anonymously")

    def login(self, username: str | int | None = None, password: str | None = None) -> bool:
        """Log in and keep the token for later requests. Returns ``True`` on success."""
        username = username if username is not None else self.username
        password = password if password is not None else self.password
        if not username or not password:
            raise AuthenticationError("Username and password are required to log in.")

        payload = {"Username": str(normalize_username(username)), "Password": str(password)}
        response = self._request("POST", "Accounts/UserLogin/", json=payload)
        if response.status_code != 200:
            message = ""
            with contextlib.suppress(ValueError):
                message = response.json().get("message", "")
            raise AuthenticationError(
                f"Login failed ({response.status_code}){': ' + message if message else ''}"
            )

        data = cast(RawLoginResponse, response.json())
        token = data.get("Token")
        if not token:
            raise AuthenticationError("Login succeeded but no token was returned.")
        user_id = data.get("User", {}).get("UserId")
        self.session_manager.set_token(token, user_id if isinstance(user_id, int) else None)
        return True

    def logout(self) -> None:
        self.session_manager.clear()

    def check_token(self) -> bool:
        """Ask the server whether the current token is still valid."""
        if not self.session_manager.auth_token:
            return False
        response = self._request("GET", "Accounts/CheckToken")
        return response.status_code == 200 and bool(response.json().get("valid"))

    def _require_login(self) -> None:
        if self.session_manager.is_token_valid():
            return
        if self.username and self.password:
            self.login()
            return
        raise SessionDisabledException()

    # ---------------------------------------------------------------- search

    def search_items(self, keyword: str, user_id: int = -1) -> Category:
        """Autocomplete search: ravs, books, categories and shiur titles."""
        encoded = quote(keyword.replace(",", ""), safe="")
        path = f"Search/WebSite_GetSearchItems/{encoded}/{user_id}/1/4"
        try:
            data = self._json("GET", path)
        except CloudflareChallengeError:
            raise
        except APIError as exc:
            raise SearchFailedException(
                f"Error fetching data for keyword: {keyword}", exc.status_code, exc.url
            ) from exc
        return self.categorize_items(cast("list[RawSearchItem]", data or []))

    def search_shiurim(
        self,
        text: str,
        *,
        limit: int | None = 24,
        page_size: int = 100,
        order: SearchOrder = SearchOrder.NEWEST,
        language: Language | None = None,
    ) -> list[Shiur]:
        """Full text search for shiurim (the site's search results page)."""
        return list(
            self.iter_search_shiurim(
                text, limit=limit, page_size=page_size, order=order, language=language
            )
        )

    def iter_search_shiurim(
        self,
        text: str,
        *,
        limit: int | None = None,
        page_size: int = 100,
        order: SearchOrder = SearchOrder.NEWEST,
        language: Language | None = None,
    ) -> Iterator[Shiur]:
        """Lazily iterate over all search results."""
        session_id: str | None = None

        def fetch(from_row: int, rows: int) -> list[Shiur]:
            nonlocal session_id
            query = self._shiurim_query(
                -1,
                from_row=from_row,
                num_rows=rows,
                order=order,
                filter_switch=_FILTERS_SEARCH,
                filter_type="default",
                language=language,
                QueryType=0,
                MainSubjectID=-1,
                CustomQueryString="0",
                CustomString=text,
                CustomBool=True,
            )
            if session_id is None:
                try:
                    data = cast(
                        RawSearchResults,
                        self._json(
                            "POST", "Search/WebSite_GetSearchResultsWithSession", json=query
                        ),
                    )
                except CloudflareChallengeError:
                    raise
                except APIError as exc:
                    raise SearchFailedException(
                        f"Error searching for {text!r}", exc.status_code, exc.url
                    ) from exc
                session_id = data.get("SessionText")
                return self.format_shiurim(data.get("ShiurimList") or [])
            query["SessionID"] = session_id
            return self._post_shiurim(
                "Search/WebSite_GetSearchResultsNextChunk", query, f"Error searching for {text!r}"
            )

        return self._paginate(fetch, page_size, limit)

    # ------------------------------------------------------------------ ravs

    def search_rav_shiurim(
        self,
        rav_id: int | str,
        from_row: int = 0,
        num_rows: int = 24,
        *,
        order: SearchOrder = SearchOrder.NEWEST,
        language: Language | None = None,
    ) -> list[Shiur]:
        """One page of a rav's shiurim."""
        rav_id = self._as_id(rav_id, "Rav ID")
        query = self._shiurim_query(
            rav_id,
            from_row=from_row,
            num_rows=num_rows,
            order=order,
            filter_switch=_FILTERS_ALL,
            filter_type="all",
            language=language,
        )
        return self._post_shiurim(
            "Search/WebSite_GetRavShiurim/",
            query,
            f"Error fetching Rav Shiurim for Rav ID {rav_id}",
        )

    def iter_rav_shiurim(
        self,
        rav_id: int | str,
        *,
        limit: int | None = None,
        page_size: int = 100,
        order: SearchOrder = SearchOrder.NEWEST,
        language: Language | None = None,
    ) -> Iterator[Shiur]:
        """Lazily iterate over all shiurim of a rav."""
        rav_id = self._as_id(rav_id, "Rav ID")
        return self._paginate(
            lambda start, rows: self.search_rav_shiurim(
                rav_id, start, rows, order=order, language=language
            ),
            page_size,
            limit,
        )

    def get_all_rav_shiurim(self, rav_id: int | str, page_size: int = 100) -> list[Shiur]:
        """Every shiur of a rav (may be thousands; prefer :meth:`iter_rav_shiurim`)."""
        return list(self.iter_rav_shiurim(rav_id, page_size=page_size))

    def get_rav(self, rav_id: int) -> Rav:
        """Name, image and number of shiurim of a rav."""
        basic = cast(RawRavBasicProp, self._json("GET", f"Ravs/GetRavBasicProp/{rav_id}/false/"))
        count = self._json("GET", f"Ravs/WebSite_GetRavShiurimCount/{rav_id}/-1")
        return Rav(
            rav_id=rav_id,
            name=basic.get("ravName", ""),
            image_file_name=basic.get("ravImageFileName"),
            shiurim_count=count.get("VarInt") if isinstance(count, dict) else None,
        )

    def get_rav_folders(self, rav_id: int, language: Language = Language.HEBREW) -> list[Folder]:
        """Main folders (series) of a rav."""
        lang = int(language) if language is not Language.ALL else int(Language.HEBREW)
        data = self._json("GET", f"Ravs/GetRavMainFolders/{rav_id}/{lang}")
        return [Folder.from_api(item) for item in cast("list[RawFolder]", data or [])]

    def search_ravs(
        self,
        text: str,
        *,
        limit: int = 24,
        offset: int = 0,
        language: Language = Language.HEBREW,
    ) -> list[Rav]:
        """Search ravs by name (the site's "rav search" page)."""
        lang = int(language) if language is not Language.ALL else int(Language.HEBREW)
        encoded = quote(text.strip(), safe="")
        data = self._json(
            "GET", f"Search/WebSite_SearchRav/{encoded}/{lang}/1/{offset}/{limit}/false"
        )
        return [Rav.from_search(item) for item in cast("list[RawRavSearchResult]", data or [])]

    def get_popular_ravs(self, language: Language = Language.HEBREW) -> list[Rav]:
        """Ravs shown in the "popular ravs" strip of the home page."""
        lang = int(language) if language is not Language.ALL else int(Language.HEBREW)
        data = self._json("GET", f"HomePage/WebSite_GetPopularRavs/{lang}")
        return [Rav.from_search(item) for item in cast("list[RawRavSearchResult]", data or [])]

    # --------------------------------------------------------------- folders

    def get_folder_shiurim(
        self,
        folder_id: int,
        from_row: int = 0,
        num_rows: int = 24,
        *,
        order: SearchOrder = SearchOrder.NEWEST,
        language: Language | None = None,
    ) -> list[Shiur]:
        """One page of shiurim under a folder (including sub folders)."""
        query = self._shiurim_query(
            folder_id,
            from_row=from_row,
            num_rows=num_rows,
            order=order,
            filter_switch=_FILTERS_NODE,
            filter_type="nodeSearch",
            language=language,
        )
        return self._post_shiurim(
            "Search/WebSite_GetShiurimUnderNode", query, f"Error fetching folder {folder_id}"
        )

    def iter_folder_shiurim(
        self,
        folder_id: int,
        *,
        limit: int | None = None,
        page_size: int = 100,
        order: SearchOrder = SearchOrder.NEWEST,
        language: Language | None = None,
    ) -> Iterator[Shiur]:
        return self._paginate(
            lambda start, rows: self.get_folder_shiurim(
                folder_id, start, rows, order=order, language=language
            ),
            page_size,
            limit,
        )

    # ---------------------------------------------------------------- shiurim

    def get_shiur_details(self, file_id: int) -> ShiurDetails:
        try:
            data = self._json("GET", f"TblShiurimLists/WebSite_GetShiurDetails/{file_id}")
        except CloudflareChallengeError:
            raise
        except APIError as exc:
            raise ShiurDetailsNotFoundException(file_id, exc.status_code) from exc
        if not data:
            raise ShiurDetailsNotFoundException(file_id)
        return ShiurDetails.from_api(cast(RawShiur, data))

    def get_play_source(
        self, file_id: int, quality: QualityLevel = QualityLevel.AUDIO
    ) -> PlaySource:
        """Streaming URL used by the site's player. Works without login."""
        data = cast(
            "RawPlayToken | None",
            self._json(
                "GET",
                f"files/GetPlayToken/{file_id}/{int(quality)}",
                headers={"Cache-Control": "no-store"},
            ),
        )
        if not data:
            raise APIError(f"No play source for file {file_id} ({quality.name})")
        token_url = (
            f"{self.API_URL}files/GetFileToPlay/{file_id}/{int(quality)}/{data['token']}"
            if data.get("token")
            else None
        )
        src = data.get("src")
        if src:
            fallback = f"{token_url}?src=cdnfail" if token_url else None
            return PlaySource(
                file_id=file_id,
                quality=quality,
                url=src,
                fallback_url=fallback,
                mode=data.get("mode"),
            )
        if token_url:
            return PlaySource(
                file_id=file_id, quality=quality, url=token_url, mode=data.get("mode")
            )
        raise APIError(f"No play source for file {file_id} ({quality.name})")

    def get_play_url(self, file_id: int, quality: QualityLevel = QualityLevel.AUDIO) -> str:
        return self.get_play_source(file_id, quality).url

    @staticmethod
    def get_audio_url(file_id: int) -> str:
        """Public MP3 URL of a shiur, the same one its RSS feed links to. No API call."""
        return urls.audio_archive_url(file_id)

    def get_attachments(self, file_id: int) -> list[Attachment]:
        """PDF attachments (sources, summaries) of a shiur."""
        data = self._json("GET", f"PlayShiur/GetTblShiurimAttachmentsByFileId/{file_id}")
        attachments = [Attachment.from_api(a) for a in cast("list[RawAttachment]", data or [])]
        return sorted(attachments, key=lambda a: a.order or 0)

    def get_live_shiurim(
        self, count: int = 20, *, language: Language = Language.HEBREW, video: bool = True
    ) -> list[LiveShiur]:
        """Shiurim broadcast live right now, with their HLS stream URLs."""
        lang = int(language) if language is not Language.ALL else int(Language.HEBREW)
        path = f"LiveShiurim/WebSite_GetLiveShiurim/{lang}/{str(video).lower()}/true/{count}/-1"
        data = self._json("GET", path)
        return [LiveShiur.from_api(item) for item in cast("list[RawLiveShiur]", data or [])]

    # -------------------------------------------------------------- download

    def get_download_key(self, file_id: int) -> str:
        self._require_login()
        response = self._request(
            "GET",
            f"files/checkAutorizationDownload/{file_id}/false",
            headers={"Cache-Control": "no-store"},
        )
        if response.status_code == 200:
            key = (response.json() or {}).get("key")
            if key:
                return str(key)
        raise DownloadKeyNotFoundException(file_id, response.status_code)

    def get_download_url(
        self, file_id: int, quality_level: QualityLevel = QualityLevel.AUDIO
    ) -> str:
        """Signed download URL (requires login). The URL itself needs no auth header."""
        key = self.get_download_key(file_id)
        quality = int(quality_level)
        return f"{self.API_URL}files/GetFileDownload/{file_id}/{quality}/{key}/null/false/false"

    def download_file(
        self,
        file_id: int,
        quality_level: QualityLevel = QualityLevel.AUDIO,
        dest: str | os.PathLike[str] = ".",
        *,
        filename: str | None = None,
        use_server_filename: bool = False,
        overwrite: bool = True,
        progress: ProgressCallback | None = None,
        chunk_size: int = 1 << 16,
    ) -> str:
        """Download a shiur with the official download endpoint (requires login).

        :param dest: target directory (created if missing).
        :param filename: file name to use; defaults to ``shiur_<id>_<quality>.<ext>``.
        :param use_server_filename: use the Hebrew title the server suggests instead.
        :param progress: ``callback(bytes_done, total_or_None)``.
        :returns: path of the saved file.
        """
        quality_level = QualityLevel(quality_level)
        url = self.get_download_url(file_id, quality_level)
        response = self._request("GET", url, stream=True)
        if response.status_code not in (200, 206):
            raise DownloadFailedException(
                "Download failed", response.status_code, file_id, quality_level
            )

        if filename is None and use_server_filename:
            match = _FILENAME_STAR.search(response.headers.get("content-disposition", ""))
            if match:
                filename = unquote(match.group(1))
        if filename is None:
            filename = f"shiur_{file_id}_{quality_level.label}.{quality_level.extension}"

        target_dir = Path(dest)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / sanitize_filename(filename)
        if target.exists() and not overwrite:
            response.close()
            return str(target)

        _save_response(response, target, progress, chunk_size)
        return str(target)

    def download_attachment(
        self,
        attachment: Attachment,
        dest: str | os.PathLike[str] = ".",
        *,
        filename: str | None = None,
        overwrite: bool = True,
    ) -> str:
        """Download a PDF attachment of a shiur. No login needed."""
        target_dir = Path(dest)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / sanitize_filename(filename or f"{attachment.title}.pdf")
        if target.exists() and not overwrite:
            return str(target)
        response = self.session.get(attachment.url, stream=True, timeout=self.timeout)
        if response.status_code != 200:
            response.close()
            raise APIError(
                f"Attachment download failed: {attachment.url}",
                response.status_code,
                attachment.url,
            )
        _save_response(response, target, None, 1 << 16)
        return str(target)

    def download_shiurim(
        self,
        shiurim: Iterable[Shiur],
        dest: str | os.PathLike[str] = ".",
        quality_level: QualityLevel = QualityLevel.AUDIO,
        *,
        filename_template: str = DEFAULT_FILENAME_TEMPLATE,
        skip_existing: bool = True,
        with_attachments: bool = False,
        on_result: Callable[[DownloadResult], None] | None = None,
    ) -> list[DownloadResult]:
        """Download many shiurim (requires login). Errors are collected, not raised.

        :param filename_template: ``str.format`` template without extension. Fields:
            ``file_id``, ``title``, ``rav``, ``rav_id``, ``folder_id``, ``date``
            (``YYYY-MM-DD``), ``quality``.
        :param skip_existing: do not download files that already exist in ``dest``.
        :param with_attachments: also save the PDF attachments next to each shiur.
        :param on_result: called after every shiur, e.g. to print progress.
        """
        quality_level = QualityLevel(quality_level)
        results: list[DownloadResult] = []
        for shiur in shiurim:
            stem = sanitize_filename(format_shiur_filename(shiur, filename_template, quality_level))
            filename = f"{stem}.{quality_level.extension}"
            target = Path(dest) / filename
            result = DownloadResult(shiur=shiur, path=str(target))
            if skip_existing and target.exists():
                result.skipped = True
            elif quality_level not in shiur.available_qualities:
                result.path = None
                result.error = f"{quality_level.label} is not available"
            else:
                try:
                    self.download_file(shiur.file_id, quality_level, dest, filename=filename)
                    if with_attachments:
                        for attachment in self.get_attachments(shiur.file_id):
                            self.download_attachment(
                                attachment,
                                dest,
                                filename=f"{stem} - {attachment.title}.pdf",
                                overwrite=not skip_existing,
                            )
                except (SessionDisabledException, AuthenticationError):
                    raise
                except KolHalashonError as exc:
                    result.path = None
                    result.error = str(exc)
            results.append(result)
            if on_result:
                on_result(result)
        return results

    def download_folder(
        self,
        folder_id: int,
        dest: str | os.PathLike[str] = ".",
        quality_level: QualityLevel = QualityLevel.AUDIO,
        *,
        limit: int | None = None,
        order: SearchOrder = SearchOrder.OLDEST,
        **kwargs: Any,
    ) -> list[DownloadResult]:
        """Download every shiur of a folder. See :meth:`download_shiurim` for options."""
        shiurim = self.iter_folder_shiurim(folder_id, limit=limit, order=order)
        return self.download_shiurim(shiurim, dest, quality_level, **kwargs)

    def download_rav(
        self,
        rav_id: int,
        dest: str | os.PathLike[str] = ".",
        quality_level: QualityLevel = QualityLevel.AUDIO,
        *,
        limit: int | None = None,
        order: SearchOrder = SearchOrder.OLDEST,
        **kwargs: Any,
    ) -> list[DownloadResult]:
        """Download every shiur of a rav. See :meth:`download_shiurim` for options."""
        shiurim = self.iter_rav_shiurim(rav_id, limit=limit, order=order)
        return self.download_shiurim(shiurim, dest, quality_level, **kwargs)

    # ------------------------------------------------------------------- RSS

    @staticmethod
    def get_rss_url(
        folder_id: int,
        rav_id: int | None = None,
        *,
        audio_only: bool = True,
        order: RssOrder = RssOrder.NEWEST,
        page: int = 1,
        language: Language = Language.HEBREW,
    ) -> str:
        """RSS (podcast) URL of a folder. No API call."""
        return build_rss_url(
            folder_id, rav_id, audio_only=audio_only, order=order, page=page, language=language
        )

    def get_shiur_rss_url(self, file_id: int, **kwargs: Any) -> str:
        """RSS URL of the folder a shiur belongs to."""
        details = self.get_shiur_details(file_id)
        if not details.folder_id:
            raise RssError(f"Shiur {file_id} is not in a folder")
        return self.get_rss_url(details.folder_id, details.rav_id, **kwargs)

    def load_rss(self, url_or_folder_id: str | int, **kwargs: Any) -> RssFeed:
        """Fetch and parse an RSS feed, given its URL or a folder id."""
        url = (
            self.get_rss_url(url_or_folder_id, **kwargs)
            if isinstance(url_or_folder_id, int)
            else url_or_folder_id
        )
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise RssError(f"Could not fetch {url}: {exc}") from exc
        if _is_cloudflare_challenge(response):
            raise CloudflareChallengeError(url, response.status_code)
        if response.status_code != 200:
            raise RssError(f"Could not fetch {url}: HTTP {response.status_code}")
        return parse_rss(response.content, url)

    def iter_rss(
        self, folder_id: int, rav_id: int | None = None, **kwargs: Any
    ) -> Iterator[RssFeed]:
        """Yield every page of a folder's RSS feed (100 items per page)."""
        page = 1
        while True:
            feed = self.load_rss(self.get_rss_url(folder_id, rav_id, page=page, **kwargs))
            if not feed.items:
                return
            yield feed
            if len(feed.items) < RSS_PAGE_SIZE:
                return
            page += 1

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _as_id(value: int | str, name: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise SearchFailedException(f"Invalid {name} format: {value!r}", 400) from exc

    @staticmethod
    def categorize_items(items: list[RawSearchItem]) -> Category:
        categories = Category()
        groups = {
            SearchItemType.RAV: categories.rabanim,
            SearchItemType.BOOK: categories.books,
            SearchItemType.SHIUR: categories.shiurim,
            SearchItemType.CATEGORY: categories.categories,
            SearchItemType.CATEGORY_ALIAS: categories.categories,
        }
        for raw in items:
            item = SearchItem.from_api(raw)
            group = groups.get(item.item_type) if item.item_type else None
            (group if group is not None else categories.others).append(item)
        return categories

    @staticmethod
    def format_shiurim(shiurim: list[RawShiur]) -> list[Shiur]:
        return [Shiur.from_api(shiur) for shiur in shiurim]
