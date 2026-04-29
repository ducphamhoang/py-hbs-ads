#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from template_catalog import render_template

VIEW_TO_TEMPLATE = {
    "active-projects": "query_projects_not_done",
    "active-tasks": "query_tasks_not_done",
    "ownerless-active-tasks": "query_tasks_missing_owner",
    "undated-active-tasks": "query_tasks_missing_due_date",
}


def prepare_view(view: str, *, variables: dict | None = None) -> dict:
    if view not in VIEW_TO_TEMPLATE:
        raise KeyError(f"Unknown common view: {view}")
    template_name = VIEW_TO_TEMPLATE[view]
    rendered = render_template(template_name, variables=variables or {})
    return {
        "view": view,
        "template_name": template_name,
        "kind": rendered["kind"],
        "data_source_id": rendered["profile"].get("data_source_id"),
        "request": rendered["request"],
        "profile": rendered["profile"],
        "description": rendered["description"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a common Notion Scrum query view")
    parser.add_argument("--view", required=True, choices=sorted(VIEW_TO_TEMPLATE))
    parser.add_argument("--page-size", type=int, default=None)
    args = parser.parse_args()

    variables = {}
    if args.page_size is not None:
        variables["page_size"] = args.page_size
    print(json.dumps(prepare_view(args.view, variables=variables), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
