"""Usage examples. Run with: uv run python examples.py"""

from kolhalashon import (
    CloudflareChallengeError,
    KolHalashonAPI,
    QualityLevel,
    RssOrder,
    SessionDisabledException,
)

RAV_ID = 7  # הרב אשר וייס
FOLDER_ID = 5761


def rss_examples(api: KolHalashonAPI) -> None:
    # Build the RSS URL of a folder (no network needed)
    print(api.get_rss_url(FOLDER_ID, RAV_ID))
    print(api.get_rss_url(FOLDER_ID, RAV_ID, order=RssOrder.OLDEST, page=2))

    # Load and parse the feed
    feed = api.load_rss(FOLDER_ID, rav_id=RAV_ID)
    print(feed.title, len(feed))
    for item in feed.items[:3]:
        print(item.published, item.file_id, item.title, item.url)


def api_examples(api: KolHalashonAPI) -> None:
    # Autocomplete search
    result = api.search_items("אשר וייס")
    for rav in result.rabanim:
        print("rav:", rav.id, rav.name)

    # Full text search
    for shiur in api.search_shiurim("אשר וייס", limit=5):
        print(shiur.file_id, shiur.title, shiur.duration)

    # Rav, folders and shiurim
    print(api.get_rav(RAV_ID))
    for folder in api.get_rav_folders(RAV_ID)[:3]:
        print(folder.folder_id, folder.title, api.get_rss_url(folder.folder_id, RAV_ID))
    for shiur in api.iter_rav_shiurim(RAV_ID, limit=5):
        print(shiur.file_id, shiur.title)

    # Details and streaming URL (no login needed)
    details = api.get_shiur_details(42863638)
    print(details.title, details.folder_id)
    print(api.get_play_url(details.file_id, QualityLevel.AUDIO))
    print(api.get_shiur_rss_url(details.file_id))

    # Download (needs KOL_HALASHON_USERNAME / KOL_HALASHON_PASSWORD)
    try:
        print(api.download_file(details.file_id, QualityLevel.AUDIO, "downloads"))
    except SessionDisabledException as exc:
        print(exc)


def main() -> None:
    api = KolHalashonAPI.from_env()
    rss_examples(api)
    try:
        api_examples(api)
    except CloudflareChallengeError as exc:
        print(exc)


if __name__ == "__main__":
    main()
