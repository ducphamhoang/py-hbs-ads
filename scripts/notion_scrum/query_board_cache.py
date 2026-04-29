#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from board_cache import DEFAULT_BOARD_CACHE, get_record, load_snapshot, lookup_exact_title


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the local Notion board cache")
    parser.add_argument("--cache", type=Path, default=DEFAULT_BOARD_CACHE)
    parser.add_argument("--kind", choices=["projects", "tasks"], required=True)
    parser.add_argument("--title")
    parser.add_argument("--id")
    args = parser.parse_args()

    snapshot = load_snapshot(args.cache)
    if args.title:
        ids = lookup_exact_title(snapshot, kind=args.kind, title=args.title)
        result = {"kind": args.kind, "title": args.title, "ids": ids}
    elif args.id:
        result = {"kind": args.kind, "id": args.id, "record": get_record(snapshot, kind=args.kind, record_id=args.id)}
    else:
        raise SystemExit("Provide either --title or --id")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
