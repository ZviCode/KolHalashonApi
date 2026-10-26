from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..utils import urls
from .enums import QualityLevel, SearchItemType
from .raw import (
    RawAttachment,
    RawFolder,
    RawLiveShiur,
    RawRavSearchResult,
    RawSearchItem,
    RawShiur,
)

_FRACTION = re.compile(r"\.(\d+)")


def parse_datetime(value: str | None) -> datetime | None:
    """Parse the server's ISO timestamps, which have 0-7 fractional digits."""
    if not value:
        return None
    normalized = _FRACTION.sub(lambda m: "." + m.group(1)[:6].ljust(6, "0"), value.rstrip("Z"))
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def parse_duration(value: str | None) -> int | None:
    """Convert ``HH:MM:SS`` (or ``MM:SS``) to seconds."""
    if not value:
        return None
    try:
        parts = [int(p) for p in value.split(":")]
    except ValueError:
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


@dataclass(kw_only=True)
class Shiur:
    """A shiur as returned by the listing/search endpoints."""

    file_id: int
    title: str = ""
    title_english: str = ""
    rav: str = ""
    rav_english: str = ""
    rav_id: int | None = None
    rav_image: str | None = None
    duration: str = "Unavailable"
    record_date: str = ""
    main_topic: str = ""
    main_topic_english: str = ""
    category_1: str = ""
    category_2: str = ""
    category_id_1: str | None = None
    category_id_2: str | None = None
    folder_id: int | None = None
    language_id: int | None = None
    audio_available: bool = False
    video_available: bool = False
    hd_video_available: bool = False
    download_count: int = 0
    women_only: bool = False
    shiur_type: str = "Unavailable"
    viewed_by_user: bool = False
    is_locked: bool = False
    download_disabled: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, data: RawShiur) -> Shiur:
        return cls(**_shiur_kwargs(data))

    @property
    def record_datetime(self) -> datetime | None:
        return parse_datetime(self.record_date)

    @property
    def duration_seconds(self) -> int | None:
        return parse_duration(self.duration)

    @property
    def available_qualities(self) -> list[QualityLevel]:
        flags = {
            QualityLevel.AUDIO: self.audio_available,
            QualityLevel.VIDEO: self.video_available,
            QualityLevel.HD_VIDEO: self.hd_video_available,
        }
        return [quality for quality, available in flags.items() if available]

    @property
    def audio_url(self) -> str:
        """Public MP3 URL (no login needed). Only valid when ``audio_available``."""
        return urls.audio_archive_url(self.file_id)

    @property
    def thumbnail_url(self) -> str:
        return urls.thumbnail_url(self.file_id)

    @property
    def page_url(self) -> str:
        return urls.shiur_page_url(self.file_id)


@dataclass(kw_only=True)
class ShiurDetails(Shiur):
    """Full details of a single shiur."""

    categories: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: RawShiur) -> ShiurDetails:
        kwargs = _shiur_kwargs(data)
        categories = [c for c in (kwargs["category_1"], kwargs["category_2"]) if c]
        return cls(categories=categories, **kwargs)


def _shiur_kwargs(data: RawShiur) -> dict[str, Any]:
    return {
        "file_id": data.get("FileId", 0),
        "title": data.get("TitleHebrew") or "",
        "title_english": data.get("TitleEnglish") or "",
        "rav": data.get("UserNameHebrew") or "",
        "rav_english": data.get("UserNameEnglish") or "",
        "rav_id": data.get("UserId"),
        "rav_image": data.get("RavImageFileName"),
        "duration": data.get("ShiurDuration") or "Unavailable",
        "record_date": data.get("RecordDate") or "",
        "main_topic": data.get("MainTopicHebrew") or "",
        "main_topic_english": data.get("MainTopicEnglish") or "",
        "category_1": data.get("CatDesc1") or "",
        "category_2": data.get("CatDesc2") or "",
        "category_id_1": data.get("CatId1"),
        "category_id_2": data.get("CatId2"),
        "folder_id": data.get("FolderId"),
        "language_id": data.get("LanguageId"),
        "audio_available": bool(data.get("HasAudio")),
        "video_available": bool(data.get("HasVideo")),
        "hd_video_available": bool(data.get("HasHdVideo")),
        "download_count": data.get("DownloadCount") or 0,
        "women_only": bool(data.get("IsWomenOnly")),
        "shiur_type": data.get("ShiurType") or "Unavailable",
        "viewed_by_user": bool(data.get("ViewdByUser")),
        "is_locked": bool(data.get("IsLocked")),
        "download_disabled": bool(data.get("DisableDownload")),
        "raw": dict(data),
    }


@dataclass(kw_only=True)
class SearchItem:
    """One autocomplete suggestion from :meth:`KolHalashonAPI.search_items`."""

    type: int
    id: int | None
    big_id: int | None = None
    str_id: str | None = None
    name: str = ""
    name_english: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, data: RawSearchItem) -> SearchItem:
        return cls(
            type=data.get("SearchItemType", 0),
            id=data.get("SearchItemId"),
            big_id=data.get("SearchItemBigId"),
            str_id=data.get("SearchItemStrId"),
            name=data.get("SearchItemTextHebrew") or "",
            name_english=data.get("SearchItemTextEnglish"),
            raw=dict(data),
        )

    @property
    def item_type(self) -> SearchItemType | None:
        try:
            return SearchItemType(self.type)
        except ValueError:
            return None

    # Backwards compatible aliases for the old dict keys.
    def __getitem__(self, key: str) -> Any:
        if key == "ID":
            return self.id
        if key == "NameHebrew":
            return self.name
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class Category:
    """Autocomplete results grouped by type."""

    rabanim: list[SearchItem] = field(default_factory=list)
    books: list[SearchItem] = field(default_factory=list)
    shiurim: list[SearchItem] = field(default_factory=list)
    categories: list[SearchItem] = field(default_factory=list)
    others: list[SearchItem] = field(default_factory=list)

    def __iter__(self) -> Iterator[SearchItem]:
        yield from self.rabanim
        yield from self.books
        yield from self.shiurim
        yield from self.categories
        yield from self.others

    def __len__(self) -> int:
        return sum(
            len(group)
            for group in (self.rabanim, self.books, self.shiurim, self.categories, self.others)
        )


@dataclass(kw_only=True)
class Folder:
    """A shiurim folder (series) of a rav."""

    folder_id: int
    rav_id: int | None = None
    title: str = ""
    title_english: str = ""
    category_id: str | None = None
    language_id: int | None = None
    has_audio: bool = False
    has_video: bool = False
    order: int | None = None
    created: datetime | None = None
    modified: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, data: RawFolder) -> Folder:
        return cls(
            folder_id=data.get("FolderId", 0),
            rav_id=data.get("RavId"),
            title=data.get("RavMainLabelHebrew") or "",
            title_english=data.get("RavMainLabelEnglish") or "",
            category_id=data.get("CatId"),
            language_id=data.get("LanguageId"),
            has_audio=bool(data.get("Audio")),
            has_video=bool(data.get("Video")),
            order=data.get("RavMainOrder"),
            created=parse_datetime(data.get("CreationDate")),
            modified=parse_datetime(data.get("LastModificationDate")),
            raw=dict(data),
        )

    @property
    def page_url(self) -> str:
        return urls.folder_page_url(self.folder_id)


@dataclass(kw_only=True)
class Rav:
    rav_id: int
    name: str
    name_english: str | None = None
    image_file_name: str | None = None
    shiurim_count: int | None = None
    download_count: int | None = None
    last_record_date: datetime | None = None
    alternative_names: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_search(cls, data: RawRavSearchResult) -> Rav:
        alternatives = data.get("AlternativeWritingWays") or ""
        return cls(
            rav_id=data.get("UserId", 0),
            name=data.get("RavSearchNameHebrew") or "",
            name_english=data.get("RavSearchNameEnglish"),
            image_file_name=data.get("RavImageFileName"),
            shiurim_count=data.get("ShiurimTotalCount") or data.get("ShiurimCount"),
            download_count=data.get("DownloadCount"),
            last_record_date=parse_datetime(data.get("LastRecordDate")),
            alternative_names=[a.strip() for a in alternatives.split(",") if a.strip()],
            raw=dict(data),
        )

    @property
    def image_url(self) -> str | None:
        return urls.rav_image_url(self.image_file_name) if self.image_file_name else None

    @property
    def page_url(self) -> str:
        return urls.rav_page_url(self.rav_id)


@dataclass(kw_only=True)
class Attachment:
    """A PDF (source sheet etc.) attached to a shiur."""

    attachment_id: int
    file_id: int
    title: str
    file_name: str
    order: int | None = None

    @classmethod
    def from_api(cls, data: RawAttachment) -> Attachment:
        return cls(
            attachment_id=data.get("Id", 0),
            file_id=data.get("FileId", 0),
            title=data.get("AttachmentDesc") or data.get("AttachmentFileName", ""),
            file_name=data.get("AttachmentFileName", ""),
            order=data.get("AttachmentOrder"),
        )

    @property
    def url(self) -> str:
        return urls.attachment_url(self.file_id, self.file_name)


@dataclass(kw_only=True)
class LiveShiur(Shiur):
    """A shiur that is being broadcast right now."""

    stream_urls: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: RawLiveShiur) -> LiveShiur:  # type: ignore[override]
        return cls(stream_urls=_live_stream_urls(data), **_shiur_kwargs(data))

    @property
    def stream_url(self) -> str | None:
        """HLS (``.m3u8``) URL of the broadcast."""
        return self.stream_urls[0] if self.stream_urls else None


def _live_stream_urls(data: RawLiveShiur) -> list[str]:
    app = data.get("LivePubApp") or ""
    name = data.get("LivePubName") or ""
    if name == "REDIRECT":
        return [u for u in app.split(";") if u]
    if not app or not name:
        return []
    return [urls.live_stream_url(app, name.split("@")[0])]


@dataclass(kw_only=True)
class PlaySource:
    """Streaming source returned by ``files/GetPlayToken``."""

    file_id: int
    quality: QualityLevel
    url: str
    fallback_url: str | None = None
    mode: str | None = None


@dataclass(kw_only=True)
class DownloadResult:
    """Outcome of one shiur in :meth:`KolHalashonAPI.download_shiurim`."""

    shiur: Shiur
    path: str | None = None
    skipped: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None
