#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from board_cache import DEFAULT_BOARD_CACHE, load_snapshot, resolve_target


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a project/task target from the local board cache")
    parser.add_argument("--cache", type=Path, default=DEFAULT_BOARD_CACHE)
    parser.add_argument("--kind", choices=["projects", "tasks"], required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--project-title", help="Optional task disambiguator: expected parent project title")
    parser.add_argument("--mode", choices=["auto", "safe", "fast"], default="auto")
    parser.add_argument("--max-cache-age-seconds", type=int, default=900)
    args = parser.parse_args()

    snapshot = load_snapshot(args.cache)
    result = resolve_target(
        snapshot=snapshot,
        kind=args.kind,
        title=args.title,
        project_title=args.project_title,
        mode=args.mode,
        max_cache_age_seconds=args.max_cache_age_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
