#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from template_catalog import render_template

TEMPLATE_NAME = "inbound_discord_reply_event"


def prepare_event(*, variables: dict | None = None) -> dict:
    rendered = render_template(TEMPLATE_NAME, variables=variables or {})
    return {
        "template_name": TEMPLATE_NAME,
        "event": rendered["event"],
        "profile": rendered["profile"],
        "description": rendered["description"],
    }


def _parse_vars(items: list[str]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for item in items:
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
        else:
            result[item] = None
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a common inbound Discord reply event payload")
    parser.add_argument("--var", action="append", default=[], help="key=value pair")
    args = parser.parse_args()
    print(json.dumps(prepare_event(variables=_parse_vars(args.var)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
