from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from kolhalashon import KolHalashonAPI, Language, RssError, RssOrder, build_rss_url, parse_rss

from .conftest import FIXTURES, FakeSession, load_fixture


def test_build_rss_url_matches_site_format() -> None:
    url = build_rss_url(5761, 7)
    parts = urlsplit(url)
    assert parts.netloc == "www.kolhalashon.com"
    assert parts.path == "/New/RSS/CreateRss.aspx"
    assert parse_qs(parts.query) == {
        "Lang": ["Hebrew"],
        "FID": ["5761"],
        "AudioOnly": ["True"],
        "RavID": ["7"],
        "Order": ["1"],
        "IsEdge": ["True"],
        "PageNum": ["1"],
        "LangID": ["1"],
    }


def test_build_rss_url_options() -> None:
    query = parse_qs(
        urlsplit(
            build_rss_url(5761, order=RssOrder.OLDEST, page=3, language=Language.ENGLISH)
        ).query
    )
    assert "RavID" not in query
    assert query["Order"] == ["2"]
    assert query["PageNum"] == ["3"]
    assert query["Lang"] == ["English"]
    assert query["LangID"] == ["2"]


def test_parse_rss_fixture() -> None:
    feed = parse_rss((FIXTURES / "rss_5761.xml").read_bytes(), "u")
    assert feed.title == "קול הלשון - הרב אשר וייס - 5761"
    assert feed.image_url == "https://www.kolhalashon.com/imgs/New/newlogo1.jpg"
    assert len(feed) == 7
    first = feed.items[0]
    assert first.file_id == 42863638
    assert first.url.startswith("https://www.kolhalashon.com/mp3/NewArchive/42863/42863638.mp3")
    assert first.published is not None and first.published.year == 2026
    assert first.length and first.length > 0


def test_parse_rss_rejects_garbage() -> None:
    with pytest.raises(RssError):
        parse_rss(b"<html>not rss")


def test_load_rss_by_folder_id(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"CreateRss\.aspx\?.*FID=5761", (FIXTURES / "rss_5761.xml").read_bytes())
    feed = api.load_rss(5761, rav_id=7)
    assert len(feed) == 7
    assert "RavID=7" in fake.calls[0].url


def test_shiur_rss_url(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"WebSite_GetShiurDetails/42863638$", load_fixture("shiur_details"))
    url = api.get_shiur_rss_url(42863638)
    assert "FID=5761" in url and "RavID=7" in url


def test_iter_rss_stops_on_short_page(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"CreateRss\.aspx", (FIXTURES / "rss_5761.xml").read_bytes())
    pages = list(api.iter_rss(5761, 7))
    assert len(pages) == 1
