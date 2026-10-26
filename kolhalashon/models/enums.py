from enum import Enum, IntEnum


class QualityLevel(IntEnum):
    """Media type ids used by the site's `files/*` endpoints."""

    AUDIO = 1
    VIDEO = 2
    HD_VIDEO = 3

    @property
    def extension(self) -> str:
        return "mp3" if self is QualityLevel.AUDIO else "mp4"

    @property
    def label(self) -> str:
        return {QualityLevel.AUDIO: "audio", QualityLevel.VIDEO: "video"}.get(self, "hd")


class SearchOrder(IntEnum):
    """Values accepted by the `SearchOrder` field of shiurim searches."""

    RELEVANCE = 1
    RAV_NAME_ASC = 2
    RAV_NAME_DESC = 3
    TITLE_ASC = 4
    TITLE_DESC = 5
    DURATION = 6
    NEWEST = 7
    OLDEST = 8
    FOLDER_ORDER = 9


class SearchItemType(IntEnum):
    """`SearchItemType` values returned by the autocomplete search."""

    RAV = 2
    BOOK = 8
    CATEGORY = 9
    SHIUR = 10
    CATEGORY_ALIAS = 12


class Language(IntEnum):
    """Shiurim language ids. `ALL` disables language filtering."""

    ALL = -1
    HEBREW = 1
    ENGLISH = 2


class RssOrder(IntEnum):
    """`Order` parameter of the RSS endpoint."""

    NEWEST = 1
    OLDEST = 2


class SiteLanguage(str, Enum):
    """`Lang` parameter of the legacy (RSS) site."""

    HEBREW = "Hebrew"
    ENGLISH = "English"
