from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import pytest

from kolhalashon import (
    AuthenticationError,
    CloudflareChallengeError,
    KolHalashonAPI,
    QualityLevel,
    SearchItemType,
    SessionDisabledException,
    ShiurDetailsNotFoundException,
    normalize_username,
)

from .conftest import FakeSession, load_fixture


def make_jwt(exp: float) -> str:
    def enc(data: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{enc({'alg': 'HS256'})}.{enc({'exp': int(exp)})}.signature"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("115988", 9115988),
        (115988, 9115988),
        ("9115988", 9115988),
        ("*12345", 912345),
        ("#1234", 1234),
    ],
)
def test_normalize_username(given: str | int, expected: int) -> None:
    assert normalize_username(given) == expected


def test_every_request_sends_random_site_key(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"WebSite_GetShiurDetails/42863638$", load_fixture("shiur_details"))
    api.get_shiur_details(42863638)
    api.get_shiur_details(42863638)
    keys = [c.headers["authorization-site-key"] for c in fake.calls]
    assert all(k.startswith("Bearer ") and len(k) == len("Bearer ") + 7 for k in keys)
    assert "authorization" not in fake.calls[0].headers


def test_search_items_groups_by_type(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"Search/WebSite_GetSearchItems/", load_fixture("search_items"))
    result = api.search_items("אשר וייס")
    assert [r.id for r in result.rabanim] == [7]
    assert result.rabanim[0]["ID"] == 7  # backwards compatible access
    assert result.rabanim[0].item_type is SearchItemType.RAV
    assert len(result.categories) == 4
    assert len(result.shiurim) == 4
    assert len(result) == 9
    assert "%D7%90" in fake.calls[0].url  # keyword is URL encoded


def test_search_shiurim_paginates_with_session(api: KolHalashonAPI, fake: FakeSession) -> None:
    first = load_fixture("search_results")
    fake.add("POST", r"WebSite_GetSearchResultsWithSession$", first)
    fake.add("POST", r"WebSite_GetSearchResultsNextChunk$", load_fixture("rav_shiurim")[:1])
    shiurim = api.search_shiurim("אשר וייס", limit=None, page_size=3)
    assert len(shiurim) == 4
    next_call = fake.calls[1]
    assert next_call.json["SessionID"] == first["SessionText"]
    assert next_call.json["FromRow"] == 3
    assert next_call.json["CustomString"] == "אשר וייס"


def test_rav_shiurim_parsing(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("POST", r"Search/WebSite_GetRavShiurim/$", load_fixture("rav_shiurim"))
    shiurim = api.search_rav_shiurim("7", num_rows=3)
    shiur = shiurim[0]
    assert shiur.file_id == 42788980
    assert shiur.rav == "הרב אשר וייס"
    assert shiur.rav_id == 7
    assert shiur.folder_id == 393905
    assert shiur.duration_seconds == 15 * 60 + 53
    assert shiur.record_datetime is not None and shiur.record_datetime.year == 2026
    assert shiur.available_qualities == list(QualityLevel)
    assert shiur.audio_url.endswith("/mp3/NewArchive/42788/42788980.mp3")
    assert fake.calls[0].json["GeneralID"] == 7


def test_iter_rav_shiurim_stops_on_short_page(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("POST", r"Search/WebSite_GetRavShiurim/$", load_fixture("rav_shiurim"))
    assert len(list(api.iter_rav_shiurim(7, page_size=5))) == 3
    assert len(fake.calls) == 1
    assert len(list(api.iter_rav_shiurim(7, limit=2))) == 3  # server ignores our row count here
    assert fake.calls[-1].json["NumOfRows"] == 2


def test_folder_shiurim_uses_node_search(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("POST", r"Search/WebSite_GetShiurimUnderNode$", load_fixture("rav_shiurim"))
    api.get_folder_shiurim(5761)
    assert fake.calls[0].json["GeneralID"] == 5761
    assert fake.calls[0].json["activefilterType"] == "nodeSearch"


def test_shiur_details(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"WebSite_GetShiurDetails/42863638$", load_fixture("shiur_details"))
    details = api.get_shiur_details(42863638)
    assert details.folder_id == 5761
    assert details.download_count == 86
    assert details.categories[0] == "שיעורים ושיחות בפרשת השבוע ומועדים"


def test_shiur_details_not_found(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"WebSite_GetShiurDetails/1$", None, status=204)
    with pytest.raises(ShiurDetailsNotFoundException):
        api.get_shiur_details(1)


def test_rav_and_folders(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"Ravs/GetRavBasicProp/7/", load_fixture("rav_basic"))
    fake.add("GET", r"Ravs/WebSite_GetRavShiurimCount/7/", {"VarInt": 3745})
    fake.add("GET", r"Ravs/GetRavMainFolders/7/1$", load_fixture("rav_folders"))
    rav = api.get_rav(7)
    assert rav.name == "הרב אשר וייס"
    assert rav.shiurim_count == 3745
    assert rav.image_url == "https://www.kolhalashon.com/imgs/Ravs/0007.jpg"
    folders = api.get_rav_folders(7)
    assert folders[0].folder_id == 87422
    assert folders[0].title.startswith("סדרת שיעורים")
    assert folders[0].created is not None


def test_play_source(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add("GET", r"files/GetPlayToken/42863638/1$", load_fixture("play_token"))
    source = api.get_play_source(42863638)
    assert source.url.startswith("https://media-cdn.kolhalashon.com/")
    assert source.fallback_url is not None and source.fallback_url.endswith("?src=cdnfail")
    assert fake.calls[0].headers["Cache-Control"] == "no-store"


def test_cloudflare_challenge_is_reported(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add(
        "GET",
        r"WebSite_GetShiurDetails/",
        b"<html><title>Just a moment...</title></html>",
        status=403,
        headers={"content-type": "text/html; charset=UTF-8"},
    )
    with pytest.raises(CloudflareChallengeError):
        api.get_shiur_details(1)


def test_download_requires_login(api: KolHalashonAPI) -> None:
    with pytest.raises(SessionDisabledException):
        api.download_file(1)


def test_login_and_download(fake: FakeSession, tmp_path: Path) -> None:
    token = make_jwt(time.time() + 3600)
    fake.add("POST", r"Accounts/UserLogin/$", {"Token": token, "User": {"UserId": 9115988}})
    fake.add("GET", r"files/checkAutorizationDownload/42863638/false$", {"key": "ABC"})
    fake.add(
        "GET",
        r"files/GetFileDownload/42863638/1/ABC/null/false/false$",
        b"ID3-data",
        headers={
            "content-type": "audio/mp3",
            "content-length": "8",
            "content-disposition": (
                "attachment; filename*=UTF-8''%D7%A9%D7%99%D7%A2%D7%95%D7%A8.mp3"
            ),
        },
    )
    api = KolHalashonAPI(
        username="115988",
        password="secret",
        use_session=True,
        session_file=tmp_path / "session.json",
        session=fake,
    )
    assert api.is_logged_in
    assert fake.calls[0].json == {"Username": "9115988", "Password": "secret"}
    saved = json.loads((tmp_path / "session.json").read_text())
    assert saved["auth_token"] == token and saved["user_id"] == 9115988

    progress: list[int] = []
    path = api.download_file(
        42863638,
        dest=tmp_path / "out",
        use_server_filename=True,
        progress=lambda d, t: progress.append(d),
    )
    assert Path(path).name == "שיעור.mp3"
    assert Path(path).read_bytes() == b"ID3-data"
    assert progress == [8]
    assert fake.calls[1].headers["authorization"] == f"Bearer {token}"

    # A second client reuses the saved token without logging in again.
    fake.calls.clear()
    again = KolHalashonAPI(
        username="115988",
        password="secret",
        use_session=True,
        session_file=tmp_path / "session.json",
        session=fake,
    )
    assert again.is_logged_in
    assert fake.calls == []


def test_expired_token_triggers_login(fake: FakeSession, tmp_path: Path) -> None:
    session_file = tmp_path / "session.json"
    session_file.write_text(json.dumps({"auth_token": make_jwt(time.time() - 10)}))
    fake.add("POST", r"Accounts/UserLogin/$", {"Token": make_jwt(time.time() + 3600), "User": {}})
    KolHalashonAPI(
        username="9115988", password="x", use_session=True, session_file=session_file, session=fake
    )
    assert len(fake.calls) == 1


def test_login_failure_message(api: KolHalashonAPI, fake: FakeSession) -> None:
    fake.add(
        "POST",
        r"Accounts/UserLogin/$",
        {"message": "Username or password is incorrect"},
        status=400,
    )
    with pytest.raises(AuthenticationError, match="incorrect"):
        api.login("115988", "wrong")
