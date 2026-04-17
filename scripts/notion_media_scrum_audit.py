#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECTS_DS_DEFAULT = "2e945d07-72af-8117-a240-000bf508da50"
TASKS_DS_DEFAULT = "2e945d07-72af-81dd-821a-000b082e6e95"
NOTION_VERSION = "2025-09-03"


def load_api_key() -> str:
    key = os.getenv("NOTION_API_KEY", "").strip()
    if key:
        return key
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("NOTION_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("NOTION_API_KEY not found in environment or ~/.hermes/.env")


def notion_request(api_key: str, method: str, url: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        text = exc.read().decode(errors="replace")
        raise RuntimeError(f"Notion API error {exc.code}: {text}") from exc


def query_all(api_key: str, data_source_id: str) -> list[dict[str, Any]]:
    url = f"https://api.notion.com/v1/data_sources/{data_source_id}/query"
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload: dict[str, Any] = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = notion_request(api_key, "POST", url, payload)
        rows.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return rows


def prop_value(p: dict[str, Any]) -> Any:
    t = p.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in p.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in p.get("rich_text", []))
    if t == "status":
        return (p.get("status") or {}).get("name")
    if t == "select":
        return (p.get("select") or {}).get("name")
    if t == "multi_select":
        return [x.get("name") for x in p.get("multi_select", [])]
    if t == "people":
        vals: list[str] = []
        for x in p.get("people", []):
            vals.append(x.get("name") or x.get("person", {}).get("email") or x.get("id"))
        return vals
    if t == "date":
        return p.get("date")
    if t == "checkbox":
        return p.get("checkbox")
    if t == "number":
        return p.get("number")
    if t == "relation":
        return [x.get("id") for x in p.get("relation", [])]
    if t == "formula":
        f = p.get("formula") or {}
        return f.get(f.get("type"))
    if t == "rollup":
        r = p.get("rollup") or {}
        return r.get(r.get("type"))
    if t == "last_edited_time":
        return p.get("last_edited_time")
    return p.get(t)


def weak_task_name(name: str) -> bool:
    s = (name or "").strip().lower()
    return s in {"", "creative", "v"}


def build_report(project_rows: list[dict[str, Any]], task_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    projects = []
    for row in project_rows:
        flat = {k: prop_value(v) for k, v in row.get("properties", {}).items()}
        projects.append(
            {
                "name": flat.get("Project name") or "",
                "status": flat.get("Status"),
                "cal_status": flat.get("Cal. Status"),
                "assignee": flat.get("Assignee") or [],
                "end_date": flat.get("End date"),
                "tasks": flat.get("Tasks Tracker") or [],
            }
        )

    tasks = []
    for row in task_rows:
        flat = {k: prop_value(v) for k, v in row.get("properties", {}).items()}
        tasks.append(
            {
                "name": flat.get("Task name") or "",
                "status": flat.get("Status"),
                "assignee": flat.get("Assignee") or [],
                "due_date": flat.get("Due date"),
                "projects": flat.get("Projects") or flat.get("Projects 1") or [],
                "past_due": flat.get("Past due") or "",
            }
        )

    active_project_statuses = {"In progress", "Not started"}
    active_task_statuses = {"In progress", "Not started"}

    active_projects = [p for p in projects if p["status"] in active_project_statuses]
    active_tasks = [t for t in tasks if t["status"] in active_task_statuses]

    projects_without_tasks = [p for p in active_projects if not p["tasks"]]
    projects_without_owner = [p for p in active_projects if not p["assignee"]]
    projects_status_mismatch = [
        p
        for p in active_projects
        if p["cal_status"]
        and p["status"]
        and str(p["cal_status"]).strip().lower() != str(p["status"]).strip().lower()
    ]

    tasks_without_project = [t for t in active_tasks if not t["projects"]]
    tasks_without_owner = [t for t in active_tasks if not t["assignee"]]
    tasks_without_due = [t for t in active_tasks if not t["due_date"]]
    past_due_tasks = [t for t in active_tasks if "Past Due" in str(t["past_due"])]
    weak_named_tasks = [t for t in active_tasks if weak_task_name(t["name"])]

    owner_project_counts = collections.Counter(
        owner for p in active_projects for owner in (p["assignee"] or ["Unassigned"])
    )
    owner_task_counts = collections.Counter(
        owner for t in active_tasks for owner in (t["assignee"] or ["Unassigned"])
    )

    sample_projects = sorted(
        active_projects,
        key=lambda x: (((x["end_date"] or {}).get("start") if x["end_date"] else None) or "9999-99-99", x["name"]),
    )[:10]
    sample_tasks = sorted(
        past_due_tasks,
        key=lambda x: (((x["due_date"] or {}).get("start") if x["due_date"] else None) or "9999-99-99", x["name"]),
    )[:10]

    counts = {
        "active_projects": len(active_projects),
        "active_tasks": len(active_tasks),
        "projects_without_tasks": len(projects_without_tasks),
        "projects_without_owner": len(projects_without_owner),
        "projects_status_mismatch": len(projects_status_mismatch),
        "tasks_without_project": len(tasks_without_project),
        "tasks_without_owner": len(tasks_without_owner),
        "tasks_without_due": len(tasks_without_due),
        "past_due_tasks": len(past_due_tasks),
        "weak_named_tasks": len(weak_named_tasks),
    }

    lines: list[str] = []
    lines.append("# Notion board audit — Projects + Tasks Tracker")
    lines.append("")
    lines.append(f"Generated: {dt.datetime.now(dt.UTC).isoformat()}")
    lines.append("")
    lines.append("## Executive summary")
    lines.append(f"- Active projects: {counts['active_projects']}")
    lines.append(f"- Active tasks: {counts['active_tasks']}")
    lines.append(f"- Active projects with no linked tasks: {counts['projects_without_tasks']}")
    lines.append(f"- Active projects with no assignee: {counts['projects_without_owner']}")
    lines.append(f"- Active projects with Status vs Cal. Status mismatch: {counts['projects_status_mismatch']}")
    lines.append(f"- Active tasks with no linked project: {counts['tasks_without_project']}")
    lines.append(f"- Active tasks with no assignee: {counts['tasks_without_owner']}")
    lines.append(f"- Active tasks with no due date: {counts['tasks_without_due']}")
    lines.append(f"- Active tasks flagged past due: {counts['past_due_tasks']}")
    lines.append(f"- Active tasks with weak/blank names: {counts['weak_named_tasks']}")
    lines.append("")
    lines.append("## Active project owner load")
    for k, v in owner_project_counts.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Active task owner load")
    for k, v in owner_task_counts.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Sample active projects")
    for p in sample_projects:
        due = (p["end_date"] or {}).get("start") if p["end_date"] else None
        lines.append(
            f"- {p['name']} | status={p['status']} | cal_status={p['cal_status']} | owner={', '.join(p['assignee']) or '∅'} | end={due or '∅'} | tasks={len(p['tasks'])}"
        )
    lines.append("")
    lines.append("## Sample risky tasks")
    if sample_tasks:
        for t in sample_tasks:
            due = (t["due_date"] or {}).get("start") if t["due_date"] else None
            lines.append(
                f"- {t['name'] or '<blank>'} | status={t['status']} | owner={', '.join(t['assignee']) or '∅'} | due={due or '∅'} | linked_projects={len(t['projects'])}"
            )
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- The board has the right 2-level shape for media ops: Projects + Tasks Tracker.")
    lines.append("- Main issue is hygiene inconsistency, not missing schema.")
    if counts["projects_status_mismatch"] > 0:
        lines.append("- Project-level execution state still has trust issues because Status and Cal. Status disagree on some active projects.")
    else:
        lines.append("- Project-level status has been standardized for current active projects; the next trust problem is task-level hygiene, not project-level mismatch.")
    lines.append("- Several active projects still do not have task-level execution detail linked in.")
    lines.append("- Several active tasks are orphaned, unassigned, undated, or too vague to manage operationally.")
    lines.append("")
    lines.append("## Next actions")
    lines.append("1. Choose one source of truth between Project Status and Cal. Status/rollups.")
    lines.append("2. Enforce minimum active-task hygiene: Task name, Project, Owner, Status, Due date.")
    lines.append("3. Standardize media-friendly execution states in Tasks Tracker, especially review/blocking states.")
    lines.append("4. Remove/archive remaining test or low-signal active tasks.")
    lines.append("5. After cleanup, automate a daily Scrum Master digest from this board.")

    return counts, "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Notion media Scrum board state.")
    parser.add_argument("--projects-ds", default=PROJECTS_DS_DEFAULT)
    parser.add_argument("--tasks-ds", default=TASKS_DS_DEFAULT)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    api_key = load_api_key()
    project_rows = query_all(api_key, args.projects_ds)
    task_rows = query_all(api_key, args.tasks_ds)
    counts, report = build_report(project_rows, task_rows)

    if args.output:
        out_path = Path(args.output).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(json.dumps({"output": str(out_path), "counts": counts}, ensure_ascii=False, indent=2))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
