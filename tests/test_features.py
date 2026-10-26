from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import pytest

from kolhalashon import (
    KolHalashonAPI,
    QualityLevel,
    SessionDisabledException,
    Shiur,
    create_session,
    format_shiur_filename,
)

from .conftest import FakeSession, load_fixture


def make_jwt(exp: float) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": int(exp)}).encode()).decode()
    return f"e30.{payload.rstrip('=')}.sig"


def test_search_ravs(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"Search/WebSite_SearchRav/.+/1/1/0/3/false$", load_fixture("search_ravs"))
    ravs = api.search_ravs("וייס", limit=3)
    assert ravs[0].rav_id > 0
    assert all(r.name for r in ravs)
    assert all(r.shiurim_count is not None for r in ravs)


def test_popular_ravs(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"HomePage/WebSite_GetPopularRavs/1$", load_fixture("search_ravs"))
    assert len(api.get_popular_ravs()) == 3


def test_attachments(api: KolHalashonAPI, fake: FakeSession, tmp_path: Path) -> None:
    fake.add("GET", r"GetTblShiurimAttachmentsByFileId/42863638$", load_fixture("attachments"))
    attachments = api.get_attachments(42863638)
    assert [a.order for a in attachments] == [1, 2]
    assert attachments[0].url == (
        "https://www.kolhalashon.com/PDF/Shiurim/42863/42863638_02496803.pdf"
    )
    fake.add("GET", r"PDF/Shiurim/42863/42863638_02496803\.pdf$", b"%PDF-1.4")
    path = api.download_attachment(attachments[0], tmp_path)
    assert Path(path).read_bytes() == b"%PDF-1.4"
    assert Path(path).name == "Lech_Lecha_he_87.pdf"


def test_live_shiurim(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add(
        "GET", r"LiveShiurim/WebSite_GetLiveShiurim/1/true/true/3/-1$", load_fixture("live_shiurim")
    )
    live = api.get_live_shiurim(3)
    assert live
    for shiur in live:
        assert shiur.stream_url is not None
        assert shiur.stream_url.endswith("/playlist.m3u8")
        assert "@" not in shiur.stream_url


def test_format_shiur_filename() -> None:
    shiur = Shiur(file_id=5, title="כותרת", rav="הרב", record_date="2026-01-02T10:00:00")
    assert format_shiur_filename(shiur) == "כותרת - הרב - 5"
    assert format_shiur_filename(shiur, "{date}_{file_id}_{quality}", QualityLevel.HD_VIDEO) == (
        "2026-01-02_5_hd"
    )


def _logged_in_api(fake: FakeSession, tmp_path: Path) -> KolHalashonAPI:
    fake.add("POST", r"Accounts/UserLogin/$", {"Token": make_jwt(time.time() + 3600), "User": {}})
    return KolHalashonAPI(
        username="9115988",
        password="x",
        use_session=True,
        session_file=tmp_path / "s.json",
        session=fake,
    )


def test_download_folder(fake: FakeSession, tmp_path: Path) -> None:
    api = _logged_in_api(fake, tmp_path)
    shiurim = load_fixture("rav_shiurim")
    shiurim[1]["HasAudio"] = False
    fake.add("POST", r"Search/WebSite_GetShiurimUnderNode$", shiurim)
    fake.add("GET", r"files/checkAutorizationDownload/\d+/false$", {"key": "K"})
    fake.add("GET", r"files/GetFileDownload/\d+/1/K/", b"mp3")
    fake.add("GET", r"GetFileDownload/42863638/", None, status=500)

    dest = tmp_path / "out"
    existing = dest / "x.mp3"
    dest.mkdir()
    existing.write_bytes(b"old")

    seen: list[int] = []
    results = api.download_folder(
        5761,
        dest,
        filename_template="{file_id}",
        on_result=lambda r: seen.append(r.shiur.file_id),
    )
    by_id = {r.shiur.file_id: r for r in results}
    assert seen == [s["FileId"] for s in shiurim]
    assert by_id[42788980].ok and (dest / "42788980.mp3").read_bytes() == b"mp3"
    assert by_id[42788979].error == "audio is not available"
    assert not by_id[42863638].ok
    assert fake.calls[1].json["SearchOrder"] == 8  # oldest first

    again = api.download_folder(5761, dest, filename_template="{file_id}")
    assert {r.shiur.file_id: r.skipped for r in again}[42788980]


def test_bulk_download_requires_login(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("POST", r"Search/WebSite_GetRavShiurim/$", load_fixture("rav_shiurim"))
    with pytest.raises(SessionDisabledException):
        api.download_rav(7, "unused")


def test_default_session_retries() -> None:
    adapter = create_session(retries=4).get_adapter("https://www.kolhalashon.com/")
    assert adapter.max_retries.total == 4  # type: ignore[attr-defined]
    assert 503 in adapter.max_retries.status_forcelist  # type: ignore[attr-defined]
