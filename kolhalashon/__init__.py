"""Typed Python wrapper for the Kol Halashon website API."""

from importlib.metadata import PackageNotFoundError, version

from .api import KolHalashonAPI, create_session, format_shiur_filename, normalize_username
from .models import (
    APIError,
    Attachment,
    AuthenticationError,
    Category,
    CloudflareChallengeError,
    DownloadFailedException,
    DownloadKeyNotFoundException,
    DownloadResult,
    Folder,
    KolHalashonError,
    Language,
    LiveShiur,
    PlaySource,
    QualityLevel,
    Rav,
    RssError,
    RssOrder,
    SearchFailedException,
    SearchItem,
    SearchItemType,
    SearchOrder,
    SessionDisabledException,
    SessionNotLoadedException,
    Shiur,
    ShiurDetails,
    ShiurDetailsNotFoundException,
    SiteLanguage,
    TokenExpiredException,
)
from .rss import RssFeed, RssItem, build_rss_url, parse_rss
from .utils import SessionManager, sanitize_filename

try:
    __version__ = version("kolhalashon")
except PackageNotFoundError:  # pragma: no cover - running from a source checkout
    __version__ = "0.0.0"

__all__ = [
    "APIError",
    "Attachment",
    "AuthenticationError",
    "Category",
    "CloudflareChallengeError",
    "DownloadFailedException",
    "DownloadKeyNotFoundException",
    "DownloadResult",
    "Folder",
    "KolHalashonAPI",
    "KolHalashonError",
    "Language",
    "LiveShiur",
    "PlaySource",
    "QualityLevel",
    "Rav",
    "RssError",
    "RssFeed",
    "RssItem",
    "RssOrder",
    "SearchFailedException",
    "SearchItem",
    "SearchItemType",
    "SearchOrder",
    "SessionDisabledException",
    "SessionManager",
    "SessionNotLoadedException",
    "Shiur",
    "ShiurDetails",
    "ShiurDetailsNotFoundException",
    "SiteLanguage",
    "TokenExpiredException",
    "__version__",
    "build_rss_url",
    "create_session",
    "format_shiur_filename",
    "normalize_username",
    "parse_rss",
    "sanitize_filename",
]
