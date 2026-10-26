"""Command line interface: ``kolhalashon --help``."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from .api import DEFAULT_FILENAME_TEMPLATE, KolHalashonAPI
from .models.enums import QualityLevel, RssOrder
from .models.exceptions import KolHalashonError
from .models.shiur import DownloadResult, Shiur

_QUALITIES = {"audio": QualityLevel.AUDIO, "video": QualityLevel.VIDEO, "hd": QualityLevel.HD_VIDEO}


def _to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            f.name: _to_jsonable(getattr(value, f.name))
            for f in dataclasses.fields(value)
            if f.name != "raw"
        }
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _print_json(value: Any) -> None:
    json.dump(_to_jsonable(value), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _print_shiurim(shiurim: Iterable[Shiur]) -> None:
    for shiur in shiurim:
        print(
            f"{shiur.file_id}\t{shiur.duration}\t{shiur.record_date[:10]}\t{shiur.rav}\t{shiur.title}"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kolhalashon", description="Kol Halashon command line client"
    )
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument(
        "--env", action="store_true", help="load credentials from .env / environment"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("items", help="autocomplete search (ravs, categories, titles)")
    p.add_argument("text")

    p = sub.add_parser("search", help="search shiurim")
    p.add_argument("text")
    p.add_argument("-n", "--limit", type=int, default=24)

    p = sub.add_parser("rav", help="list shiurim of a rav")
    p.add_argument("rav_id", type=int)
    p.add_argument("-n", "--limit", type=int, default=24)

    p = sub.add_parser("folders", help="list the main folders of a rav")
    p.add_argument("rav_id", type=int)

    p = sub.add_parser("folder", help="list shiurim in a folder")
    p.add_argument("folder_id", type=int)
    p.add_argument("-n", "--limit", type=int, default=24)

    p = sub.add_parser("details", help="show details of a shiur")
    p.add_argument("file_id", type=int)

    p = sub.add_parser("url", help="print a streaming URL of a shiur")
    p.add_argument("file_id", type=int)
    p.add_argument("-q", "--quality", choices=_QUALITIES, default="audio")

    p = sub.add_parser("rss", help="print (or load) the RSS feed of a folder")
    p.add_argument("folder_id", type=int, nargs="?")
    p.add_argument("--rav", type=int, help="rav id")
    p.add_argument("--shiur", type=int, help="use the folder of this shiur instead")
    p.add_argument("--oldest", action="store_true", help="oldest first")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--load", action="store_true", help="fetch the feed and list its items")

    p = sub.add_parser("download", help="download a shiur (requires login)")
    p.add_argument("file_id", type=int)
    p.add_argument("-q", "--quality", choices=_QUALITIES, default="audio")
    p.add_argument("-o", "--dest", default=".")
    p.add_argument(
        "--server-name", action="store_true", help="use the Hebrew file name from the server"
    )

    p = sub.add_parser("ravs", help="search ravs by name")
    p.add_argument("text")
    p.add_argument("-n", "--limit", type=int, default=24)

    sub.add_parser("popular", help="list popular ravs")

    p = sub.add_parser("live", help="list live shiurim with their stream URLs")
    p.add_argument("-n", "--limit", type=int, default=20)

    p = sub.add_parser("attachments", help="list (or download) the PDF attachments of a shiur")
    p.add_argument("file_id", type=int)
    p.add_argument("-o", "--dest", help="download into this directory")

    for name, target in (("download-folder", "folder_id"), ("download-rav", "rav_id")):
        p = sub.add_parser(name, help=f"download every shiur of a {target[:-3]} (requires login)")
        p.add_argument(target, type=int)
        p.add_argument("-q", "--quality", choices=_QUALITIES, default="audio")
        p.add_argument("-o", "--dest", default=".")
        p.add_argument("-n", "--limit", type=int)
        p.add_argument(
            "-t",
            "--template",
            default=DEFAULT_FILENAME_TEMPLATE,
            help="file name template; fields: file_id title rav rav_id folder_id date quality",
        )
        p.add_argument("--attachments", action="store_true", help="also save PDF attachments")
    return parser


def _run(args: argparse.Namespace) -> None:
    api = KolHalashonAPI.from_env() if args.env else KolHalashonAPI()
    out_json: bool = args.json

    if args.command == "items":
        category = api.search_items(args.text)
        if out_json:
            _print_json(list(category))
        else:
            for item in category:
                print(f"{item.type}\t{item.id or item.str_id}\t{item.name}")
    elif args.command in ("search", "rav", "folder"):
        if args.command == "search":
            shiurim = api.search_shiurim(args.text, limit=args.limit)
        elif args.command == "rav":
            shiurim = list(api.iter_rav_shiurim(args.rav_id, limit=args.limit))
        else:
            shiurim = list(api.iter_folder_shiurim(args.folder_id, limit=args.limit))
        if out_json:
            _print_json(shiurim)
        else:
            _print_shiurim(shiurim)
    elif args.command == "folders":
        folders = api.get_rav_folders(args.rav_id)
        if out_json:
            _print_json(folders)
        else:
            for folder in folders:
                print(f"{folder.folder_id}\t{folder.title}")
    elif args.command == "details":
        details = api.get_shiur_details(args.file_id)
        if out_json:
            _print_json(details)
        else:
            for key, value in _to_jsonable(details).items():
                print(f"{key}: {value}")
    elif args.command == "url":
        print(api.get_play_url(args.file_id, _QUALITIES[args.quality]))
    elif args.command == "rss":
        _run_rss(api, args)
    elif args.command == "download":
        path = api.download_file(
            args.file_id,
            _QUALITIES[args.quality],
            args.dest,
            use_server_filename=args.server_name,
            progress=lambda done, total: print(
                f"\r{done // 1024} KiB" + (f" / {total // 1024} KiB" if total else ""),
                end="",
                file=sys.stderr,
            ),
        )
        print(file=sys.stderr)
        print(path)
    elif args.command in ("ravs", "popular"):
        ravs = (
            api.search_ravs(args.text, limit=args.limit)
            if args.command == "ravs"
            else api.get_popular_ravs()
        )
        if out_json:
            _print_json(ravs)
        else:
            for rav in ravs:
                print(f"{rav.rav_id}\t{rav.shiurim_count or ''}\t{rav.name}")
    elif args.command == "live":
        live = api.get_live_shiurim(args.limit)
        if out_json:
            _print_json(live)
        else:
            for shiur in live:
                print(f"{shiur.rav}\t{shiur.main_topic}\t{shiur.stream_url or ''}")
    elif args.command == "attachments":
        attachments = api.get_attachments(args.file_id)
        if args.dest:
            for attachment in attachments:
                print(api.download_attachment(attachment, args.dest))
        elif out_json:
            _print_json(attachments)
        else:
            for attachment in attachments:
                print(f"{attachment.title}\t{attachment.url}")
    elif args.command in ("download-folder", "download-rav"):
        _run_bulk_download(api, args)


def _run_bulk_download(api: KolHalashonAPI, args: argparse.Namespace) -> None:
    def report(result: DownloadResult) -> None:
        status = "skip" if result.skipped else "ok" if result.ok else f"error: {result.error}"
        print(f"{result.shiur.file_id}\t{status}\t{result.path or result.shiur.title}")

    options: dict[str, Any] = {
        "limit": args.limit,
        "filename_template": args.template,
        "with_attachments": args.attachments,
        "on_result": report,
    }
    quality = _QUALITIES[args.quality]
    if args.command == "download-folder":
        results = api.download_folder(args.folder_id, args.dest, quality, **options)
    else:
        results = api.download_rav(args.rav_id, args.dest, quality, **options)
    failed = sum(1 for r in results if not r.ok)
    print(f"{len(results)} shiurim, {failed} failed", file=sys.stderr)


def _run_rss(api: KolHalashonAPI, args: argparse.Namespace) -> None:
    order = RssOrder.OLDEST if args.oldest else RssOrder.NEWEST
    if args.shiur:
        url = api.get_shiur_rss_url(args.shiur, order=order, page=args.page)
    elif args.folder_id is not None:
        url = api.get_rss_url(args.folder_id, args.rav, order=order, page=args.page)
    else:
        raise SystemExit("rss: pass a folder id or --shiur FILE_ID")
    if not args.load:
        print(url)
        return
    feed = api.load_rss(url)
    if args.json:
        _print_json(feed)
        return
    print(f"# {feed.title} ({len(feed)} items)\n# {url}")
    for item in feed:
        date = item.published.date().isoformat() if item.published else ""
        print(f"{date}\t{item.title}\t{item.url}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        _run(args)
    except KolHalashonError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
