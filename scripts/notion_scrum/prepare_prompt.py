#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from template_catalog import render_template

PROMPT_KIND_TO_TEMPLATE = {
    "task-due-date": "prompt_task_due_date_request",
    "task-status": "prompt_task_status_request",
}


def prepare_prompt(kind: str, *, variables: dict | None = None) -> dict:
    if kind not in PROMPT_KIND_TO_TEMPLATE:
        raise KeyError(f"Unknown prompt kind: {kind}")
    template_name = PROMPT_KIND_TO_TEMPLATE[kind]
    rendered = render_template(template_name, variables=variables or {})
    return {
        "kind": kind,
        "template_name": template_name,
        "prompt": rendered["prompt"],
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
    parser = argparse.ArgumentParser(description="Render a common Notion Scrum prompt payload")
    parser.add_argument("--kind", required=True, choices=sorted(PROMPT_KIND_TO_TEMPLATE))
    parser.add_argument("--var", action="append", default=[], help="key=value pair")
    args = parser.parse_args()
    print(json.dumps(prepare_prompt(args.kind, variables=_parse_vars(args.var)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
