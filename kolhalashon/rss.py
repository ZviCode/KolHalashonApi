"""RSS feeds of Kol Halashon folders.

Every folder (series) on the site has a podcast style RSS feed, served by the
legacy site at ``/New/RSS/CreateRss.aspx``. Each page holds up to 100 items.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

from .models.enums import Language, RssOrder, SiteLanguage
from .models.exceptions import RssError
from .utils.urls import RSS_URL

RSS_PAGE_SIZE = 100

_FILE_ID_IN_URL = re.compile(r"/(\d{5,})\.(?:mp3|mp4)")


@dataclass(kw_only=True)
class RssItem:
    title: str
    url: str
    published: datetime | None = None
    length: int | None = None
    mime_type: str | None = None

    @property
    def file_id(self) -> int | None:
        """Shiur file id parsed from the enclosure URL."""
        match = _FILE_ID_IN_URL.search(self.url)
        return int(match.group(1)) if match else None


@dataclass(kw_only=True)
class RssFeed:
    url: str
    title: str
    link: str | None = None
    description: str | None = None
    image_url: str | None = None
    language: str | None = None
    items: list[RssItem] = field(default_factory=list)

    def __iter__(self) -> Iterator[RssItem]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


def build_rss_url(
    folder_id: int,
    rav_id: int | None = None,
    *,
    audio_only: bool = True,
    order: RssOrder = RssOrder.NEWEST,
    page: int = 1,
    language: Language = Language.HEBREW,
) -> str:
    """Build the RSS URL of a folder.

    ``rav_id`` is optional for the server but is part of the URLs the site
    itself used to publish, so pass it when known.
    """
    site_language = SiteLanguage.ENGLISH if language is Language.ENGLISH else SiteLanguage.HEBREW
    params: dict[str, str | int] = {"Lang": site_language.value, "FID": folder_id}
    params["AudioOnly"] = str(audio_only)
    if rav_id is not None:
        params["RavID"] = rav_id
    params.update(
        {
            "Order": int(order),
            "IsEdge": "True",
            "PageNum": page,
            "LangID": int(language) if language is not Language.ALL else int(Language.HEBREW),
        }
    )
    return f"{RSS_URL}?{urlencode(params)}"


def _text(element: ET.Element | None, path: str) -> str | None:
    if element is None:
        return None
    found = element.find(path)
    if found is None or found.text is None:
        return None
    return found.text.strip()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def parse_rss(content: bytes | str, url: str = "") -> RssFeed:
    """Parse the XML of a Kol Halashon RSS feed."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    content = content.lstrip(b"\xef\xbb\xbf").strip()
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise RssError(f"Invalid RSS XML from {url or 'input'}: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        raise RssError(f"RSS from {url or 'input'} has no <channel>")

    items: list[RssItem] = []
    for node in channel.findall("item"):
        enclosure = node.find("enclosure")
        item_url = (enclosure.get("url") if enclosure is not None else None) or _text(node, "link")
        if not item_url:
            continue
        length = enclosure.get("length") if enclosure is not None else None
        items.append(
            RssItem(
                title=_text(node, "title") or "",
                url=item_url,
                published=_parse_date(_text(node, "pubDate")),
                length=int(length) if length and length.isdigit() else None,
                mime_type=enclosure.get("type") if enclosure is not None else None,
            )
        )

    return RssFeed(
        url=url,
        title=_text(channel, "title") or "",
        link=_text(channel, "link"),
        description=_text(channel, "description"),
        image_url=_text(channel, "image/url"),
        language=_text(channel, "language"),
        items=items,
    )
