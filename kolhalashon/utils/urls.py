"""Builders for public kolhalashon.com URLs that need no API call."""

from __future__ import annotations

from urllib.parse import quote

BASE_URL = "https://www.kolhalashon.com/"
API_URL = f"{BASE_URL}api/"
RSS_URL = f"{BASE_URL}New/RSS/CreateRss.aspx"
STREAMING_URL = f"{BASE_URL}streaming/"

_FILE_NAME_LENGTH = 8


def shiur_file_name(file_id: int) -> str:
    """Zero padded file name the site uses for a shiur (``895822`` -> ``00895822``)."""
    return str(file_id).zfill(_FILE_NAME_LENGTH)


def shiur_folder_name(file_id: int) -> str:
    """Storage folder of a shiur: the first 5 digits of its padded file name."""
    return shiur_file_name(file_id)[:5]


def audio_archive_url(file_id: int) -> str:
    """Public MP3 URL, the same one the RSS feeds use as enclosure."""
    return f"{BASE_URL}mp3/NewArchive/{shiur_folder_name(file_id)}/{shiur_file_name(file_id)}.mp3"


def thumbnail_url(file_id: int) -> str:
    return (
        f"{BASE_URL}imgs/VideoThumbNails/{shiur_folder_name(file_id)}/"
        f"{shiur_file_name(file_id)}.webp"
    )


def rav_image_url(image_file_name: str) -> str:
    return f"{BASE_URL}imgs/Ravs/{quote(image_file_name)}"


def shiur_page_url(file_id: int, lang: str = "he") -> str:
    return f"{BASE_URL}{lang}/regularSite/playShiur/{file_id}"


def rav_page_url(rav_id: int, lang: str = "he") -> str:
    return f"{BASE_URL}{lang}/regularSite/ravs/{rav_id}"


def folder_page_url(folder_id: int, lang: str = "he") -> str:
    return f"{BASE_URL}{lang}/regularSite/treeSearch/{folder_id}"


def attachment_url(file_id: int, attachment_file_name: str) -> str:
    return f"{BASE_URL}PDF/Shiurim/{shiur_folder_name(file_id)}/{quote(attachment_file_name)}.pdf"


def live_stream_url(app: str, stream_name: str) -> str:
    return f"{STREAMING_URL}{app}/{stream_name}/playlist.m3u8"
