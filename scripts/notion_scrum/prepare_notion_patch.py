#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from template_catalog import render_template

PATCH_KIND_TO_TEMPLATE = {
    "status": "update_page_status",
    "rich-text": "update_page_rich_text",
    "date": "update_page_date",
}


def prepare_patch(kind: str, *, variables: dict | None = None) -> dict:
    if kind not in PATCH_KIND_TO_TEMPLATE:
        raise KeyError(f"Unknown patch kind: {kind}")
    template_name = PATCH_KIND_TO_TEMPLATE[kind]
    rendered = render_template(template_name, variables=variables or {})
    return {
        "kind": kind,
        "template_name": template_name,
        "request": rendered["request"],
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
    parser = argparse.ArgumentParser(description="Render a common Notion Scrum page patch payload")
    parser.add_argument("--kind", required=True, choices=sorted(PATCH_KIND_TO_TEMPLATE))
    parser.add_argument("--var", action="append", default=[], help="key=value pair")
    args = parser.parse_args()
    print(json.dumps(prepare_patch(args.kind, variables=_parse_vars(args.var)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
