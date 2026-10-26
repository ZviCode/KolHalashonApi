"""TypedDicts describing the raw JSON returned by the Kol Halashon API.

Only the fields this library reads are guaranteed; the server may add more.
"""

from __future__ import annotations

from typing import TypedDict


class RawSearchItem(TypedDict, total=False):
    SearchItemType: int
    SearchItemId: int | None
    SearchItemBigId: int | None
    SearchItemStrId: str | None
    SearchItemTextHebrew: str | None
    SearchItemTextEnglish: str | None


class RawShiur(TypedDict, total=False):
    FileId: int
    UserId: int
    UserNameHebrew: str | None
    UserNameEnglish: str | None
    RavImageFileName: str | None
    ShiurDuration: str | None
    TitleHebrew: str | None
    TitleEnglish: str | None
    LanguageId: int | None
    MainTopicHebrew: str | None
    MainTopicEnglish: str | None
    RecordDate: str | None
    FolderId: int | None
    ImageType: int | None
    HasAudio: bool | None
    HasVideo: bool | None
    HasHdVideo: bool | None
    CatId1: str | None
    CatDesc1: str | None
    CatDescEnglish1: str | None
    CatId2: str | None
    CatDesc2: str | None
    CatDescEnglish2: str | None
    DisableDownload: bool | None
    IsLocked: bool | None
    DownloadCount: int | None
    ShiurType: str | None
    IsWomenOnly: bool | None
    ViewdByUser: bool | None


class RawSearchResults(TypedDict):
    ShiurimList: list[RawShiur]
    SessionText: str


class RawFolder(TypedDict, total=False):
    FolderId: int
    RavId: int
    CatId: str | None
    LanguageId: int | None
    Audio: bool | None
    Video: bool | None
    RavMainLabelHebrew: str | None
    RavMainLabelEnglish: str | None
    RavMainOrder: int | None
    CreationDate: str | None
    LastModificationDate: str | None
    DisableDownload: bool | None
    IsLocked: bool | None


class RawRavBasicProp(TypedDict):
    ravName: str
    ravImageFileName: str | None


class RawPlayToken(TypedDict, total=False):
    src: str | None
    token: str | None
    mode: str | None


class RawLoginResponse(TypedDict, total=False):
    Token: str
    User: dict[str, object]
    ExtendedUser: dict[str, object]


class RawRavSearchResult(TypedDict, total=False):
    UserId: int
    UserType: int | None
    RavSearchNameHebrew: str | None
    RavSearchNameEnglish: str | None
    ShiurimCount: int | None
    ShiurimTotalCount: int | None
    DownloadCount: int | None
    AlternativeWritingWays: str | None
    LastRecordDate: str | None
    RavImageFileName: str | None


class RawAttachment(TypedDict, total=False):
    Id: int
    FileId: int
    AttachmentType: int | None
    AttachmentDesc: str | None
    AttachmentFileName: str
    AttachmentOrder: int | None


class RawLiveShiur(RawShiur, total=False):
    LivePubApp: str | None
    LivePubName: str | None
    QueryType: int | None
