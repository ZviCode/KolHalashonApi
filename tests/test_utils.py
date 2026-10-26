from __future__ import annotations

from kolhalashon import sanitize_filename
from kolhalashon.cli import main
from kolhalashon.models.shiur import parse_datetime, parse_duration
from kolhalashon.utils import urls


def test_sanitize_filename() -> None:
    assert sanitize_filename('פרשת "לך לך": שיעור?/א') == "פרשת ''לך לך'' שיעורא"
    assert sanitize_filename("  ...  ") == "untitled"
    assert len(sanitize_filename("א" * 500)) == 180


def test_media_urls() -> None:
    assert (
        urls.audio_archive_url(895822)
        == "https://www.kolhalashon.com/mp3/NewArchive/00895/00895822.mp3"
    )
    assert urls.thumbnail_url(42863638).endswith("/imgs/VideoThumbNails/42863/42863638.webp")


def test_parse_helpers() -> None:
    assert parse_duration("01:02:03") == 3723
    assert parse_duration("bad") is None
    parsed = parse_datetime("2026-10-22T21:06:28.543")
    assert parsed is not None and parsed.microsecond == 543000
    assert parse_datetime("2026-10-22T21:06:28.5433333") is not None
    assert parse_datetime(None) is None


def test_cli_rss_url(capsys: object) -> None:
    assert main(["rss", "5761", "--rav", "7"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "FID=5761" in out
