#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import staffing_risk
from board_cache import _compact_task
from common import load_api_key, notion_request
from query_common_view import prepare_view

ICT = timezone(timedelta(hours=7))
TEXT_BLOCK_TYPES = {
    "paragraph",
    "heading_1",
    "heading_2",
    "heading_3",
    "bulleted_list_item",
    "numbered_list_item",
    "to_do",
    "quote",
    "toggle",
    "callout",
}
PLACEHOLDER_CONTENT_MARKERS = {
    "provide an overview of the project’s goals and context",
    "provide an overview of the project's goals and context",
    "tbu",
    "tbd",
    "todo",
}
DOD_MARKERS = (
    "definition of done",
    "dod",
    "done when",
    "tiêu chí hoàn thành",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))



def _build_people_maps(registry: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    notion_user_to_person: dict[str, str] = {}
    discord_identity_by_person: dict[str, dict[str, str]] = {}
    for person_key, person in (registry.get("people") or {}).items():
        notion = person.get("notion") or {}
        user_id = notion.get("user_id")
        if user_id:
            notion_user_to_person[user_id] = person_key
        for ident in person.get("platform_identities") or []:
            if ident.get("platform") == "discord" and ident.get("platform_user_id"):
                user_id = ident["platform_user_id"]
                discord_identity_by_person[person_key] = {
                    "mention": f"<@{user_id}>",
                    "user_id": user_id,
                }
                break
    return notion_user_to_person, discord_identity_by_person



def _query_all(api_key: str, view_name: str) -> list[dict[str, Any]]:
    prepared = prepare_view(view_name)
    dsid = prepared["data_source_id"]
    body = dict(prepared["request"])
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload = dict(body)
        if cursor:
            payload["start_cursor"] = cursor
        response = notion_request(api_key, "POST", f"https://api.notion.com/v1/data_sources/{dsid}/query", payload)
        results.extend(response.get("results") or [])
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
        if not cursor:
            raise RuntimeError(f"missing next_cursor for {view_name}")
    return results



def _relation_ids(prop: dict[str, Any] | None) -> list[str]:
    if not prop:
        return []
    return [item.get("id") for item in (prop.get("relation") or []) if item.get("id")]



def _people_value(prop: dict[str, Any] | None) -> list[dict[str, str]]:
    if not prop:
        return []
    return [
        {"id": person.get("id"), "name": person.get("name")}
        for person in (prop.get("people") or [])
        if person.get("id") or person.get("name")
    ]



def _text_value(prop: dict[str, Any] | None, field: str) -> str:
    if not prop:
        return ""
    return "".join(item.get("plain_text", "") for item in (prop.get(field) or [])).strip()



def _status_name(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    return ((prop.get("status") or {}).get("name") or None)



def _date_start(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    date_value = prop.get("date") or {}
    return date_value.get("start") or None



def _compact_project(page: dict[str, Any], notion_user_to_person: dict[str, str]) -> dict[str, Any]:
    props = page.get("properties") or {}
    owners = _people_value(props.get("Project lead") or props.get("Assignee") or props.get("Owner"))
    task_ids = _relation_ids(props.get("Tasks Tracker"))
    owner_ids = [item.get("id") for item in owners if item.get("id")]
    return {
        "id": page.get("id"),
        "title": _text_value(props.get("Project name") or props.get("Name"), "title"),
        "status": _status_name(props.get("Status")),
        "start_date": _date_start(props.get("Start date")),
        "end_date": _date_start(props.get("End date")),
        "owner_ids": owner_ids,
        "owner_names": [item.get("name") for item in owners if item.get("name")],
        "owner_person_keys": [notion_user_to_person[owner_id] for owner_id in owner_ids if owner_id in notion_user_to_person],
        "task_ids": task_ids,
        "url": page.get("url"),
        "last_edited_time": page.get("last_edited_time"),
    }



def _compact_task_with_people(page: dict[str, Any], project_titles: dict[str, str], notion_user_to_person: dict[str, str]) -> dict[str, Any]:
    task = _compact_task(page, project_titles)
    owner_person_keys = [notion_user_to_person[owner_id] for owner_id in task.get("owner_ids") or [] if owner_id in notion_user_to_person]
    task["owner_person_keys"] = owner_person_keys
    return task



def _fetch_block_texts(api_key: str, block_id: str) -> list[dict[str, str]]:
    response = notion_request(api_key, "GET", f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100")
    blocks = []
    for block in response.get("results") or []:
        block_type = block.get("type")
        text = ""
        if block_type in TEXT_BLOCK_TYPES:
            text = "".join(part.get("plain_text", "") for part in ((block.get(block_type) or {}).get("rich_text") or [])).strip()
        blocks.append({"type": block_type or "unknown", "text": text})
    return blocks



def _normalized_texts(blocks: list[dict[str, str]]) -> list[str]:
    texts = []
    for block in blocks:
        text = (block.get("text") or "").strip()
        if text:
            texts.append(text)
    return texts



def analyze_project_hygiene(project: dict[str, Any], blocks: list[dict[str, str]]) -> dict[str, Any]:
    texts = _normalized_texts(blocks)
    normalized = [text.casefold() for text in texts]
    content_texts = [
        (block.get("text") or "").strip()
        for block in blocks
        if (block.get("text") or "").strip() and block.get("type") not in {"heading_1", "heading_2", "heading_3"}
    ]
    meaningful_texts = [
        text
        for text in content_texts
        if text.casefold() not in PLACEHOLDER_CONTENT_MARKERS and not text.lower().startswith("[hermes scrum] dod confirmed")
    ]
    has_dod = any(any(marker in text for marker in DOD_MARKERS) for text in normalized)
    unclear_content = len(meaningful_texts) == 0 or all(text.casefold() in PLACEHOLDER_CONTENT_MARKERS for text in meaningful_texts)
    return {
        **project,
        "missing_subtasks": len(project.get("task_ids") or []) == 0,
        "unclear_content": unclear_content,
        "missing_definition_of_done": not has_dod,
        "block_texts": texts,
    }



def _owner_label(
    person_keys: list[str],
    discord_identity_by_person: dict[str, dict[str, str]],
    owner_names: list[str] | None = None,
    *,
    mention_style: str = "discord",
) -> str:
    owner_names = owner_names or []
    identity: dict[str, str] = {}
    for person_key in person_keys:
        identity = discord_identity_by_person.get(person_key, {})
        if identity:
            break
    mention = identity.get("mention", "")
    discord_user_id = identity.get("user_id", "")
    owner_name = owner_names[0] if owner_names else ""
    token_mention = f"@@discord_user_id:{discord_user_id}@@" if discord_user_id else ""
    rendered_mention = token_mention if mention_style == "token" and token_mention else mention
    if rendered_mention and owner_name:
        return f"{rendered_mention} ({owner_name})"
    if rendered_mention:
        return rendered_mention
    if owner_name:
        return owner_name
    return ""



def _group_tasks(items: list[dict[str, Any]]) -> dict[tuple[str, tuple[str, ...]], list[str]]:
    grouped: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    for item in items:
        key = (
            item.get("project_titles", [item.get("project") or "Unknown project"])[0] if item.get("project_titles") else (item.get("project") or "Unknown project"),
            tuple(item.get("owner_person_keys") or []),
        )
        grouped.setdefault(key, []).append(item.get("title") or item.get("task") or "<untitled>")
    return grouped



def _aggregate_project_warnings(report: dict[str, Any]) -> list[dict[str, Any]]:
    aggregated: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}

    def ensure_entry(title: str, owner_person_keys: list[str] | tuple[str, ...], owner_names: list[str]) -> dict[str, Any]:
        key = (title, tuple(owner_person_keys or []))
        entry = aggregated.get(key)
        if entry is None:
            entry = {
                "title": title,
                "owner_person_keys": list(owner_person_keys or []),
                "owner_names": owner_names or [],
                "issues": [],
            }
            aggregated[key] = entry
        elif not entry.get("owner_names") and owner_names:
            entry["owner_names"] = owner_names
        return entry

    for project in report.get("projects_missing_subtasks") or []:
        ensure_entry(
            project["title"],
            project.get("owner_person_keys") or [],
            project.get("owner_names") or [],
        )["issues"].append("sub task")
    for project in report.get("projects_unclear_content") or []:
        ensure_entry(
            project["title"],
            project.get("owner_person_keys") or [],
            project.get("owner_names") or [],
        )["issues"].append("nội dung rõ ràng")
    for project in report.get("projects_missing_definition_of_done") or []:
        ensure_entry(
            project["title"],
            project.get("owner_person_keys") or [],
            project.get("owner_names") or [],
        )["issues"].append("Definition of Done")

    ownerless_groups = _group_tasks(report.get("ownerless_tasks") or [])
    undated_groups = _group_tasks(report.get("undated_tasks") or [])
    for (project_title, owner_keys), tasks in ownerless_groups.items():
        sample = next(
            (
                item
                for item in (report.get("ownerless_tasks") or [])
                if ((item.get("project_titles") or [item.get("project") or "Unknown project"])[0] == project_title
                    and tuple(item.get("owner_person_keys") or []) == owner_keys)
            ),
            None,
        )
        ensure_entry(
            project_title,
            list(owner_keys),
            (sample or {}).get("owner_names") or [],
        )["issues"].append(f"{len(tasks)} task thiếu owner ({'; '.join(tasks)})")
    for (project_title, owner_keys), tasks in undated_groups.items():
        sample = next(
            (
                item
                for item in (report.get("undated_tasks") or [])
                if ((item.get("project_titles") or [item.get("project") or "Unknown project"])[0] == project_title
                    and tuple(item.get("owner_person_keys") or []) == owner_keys)
            ),
            None,
        )
        ensure_entry(
            project_title,
            list(owner_keys),
            (sample or {}).get("owner_names") or [],
        )["issues"].append(f"{len(tasks)} task thiếu due date ({'; '.join(tasks)})")

    return list(aggregated.values())



def format_daily_check_message(
    report: dict[str, Any],
    discord_identity_by_person: dict[str, dict[str, str]],
    *,
    mention_style: str = "discord",
) -> str:
    counts = report["counts"]
    lines = [
        f"[Daily Check | {report['generated_at_ict']}]",
        "",
        f"- Active projects: {counts['active_projects']}",
        f"- Active tasks: {counts['active_tasks']}",
        f"- Overdue: {counts['overdue_tasks']}",
        f"- Tasks thiếu due date: {counts['missing_due_date']}",
        f"- Tasks thiếu owner: {counts['missing_owner']}",
        f"- Projects thiếu sub task: {counts['projects_missing_subtasks']}",
        f"- Projects thiếu nội dung rõ ràng: {counts['projects_unclear_content']}",
        f"- Projects thiếu DoD: {counts['projects_missing_definition_of_done']}",
    ]

    if report.get("action_items"):
        lines.extend(["", "**Cần action hôm nay**"])
        for item in report["action_items"]:
            owner = _owner_label(
                item.get("owner_person_keys") or [],
                discord_identity_by_person,
                item.get("owner_names") or [],
                mention_style=mention_style,
            )
            prefix = f"- {owner} " if owner else "- "
            due = item.get("due_date") or "∅"
            if item.get("is_overdue"):
                status_text = f"đang **overdue** (due **{due}**, status **{item.get('status') or 'Unknown'}**)"
            else:
                status_text = f"**đến hạn hôm nay** (**{due}**, status **{item.get('status') or 'Unknown'}**)"
            lines.append(f"{prefix}task **{item.get('title') or item.get('task') or '<untitled>'}** của project **{item.get('project')}** {status_text}")

    project_warnings = _aggregate_project_warnings(report)
    warning_lines: list[str] = []
    for project in project_warnings:
        owner = _owner_label(
            project.get("owner_person_keys") or [],
            discord_identity_by_person,
            project.get("owner_names") or [],
            mention_style=mention_style,
        )
        prefix = f"- {owner} " if owner else "- "
        warning_lines.append(
            f"{prefix}project **{project['title']}** thiếu: **{'; '.join(project.get('issues') or [])}**"
        )

    if warning_lines:
        lines.extend(["", "**Cảnh báo theo project**", *warning_lines])

    # ── Staffing sections (RPT-02, RPT-03) ──────────────────────────────
    staffing_risks = report.get("staffing_risks")
    if staffing_risks:
        risks = staffing_risks.get("risks", {})

        # Section: absent owners WITH backup
        absent_with_backup = [t for t in risks.get("absent_owner_tasks", []) if t.get("backup_key")]
        absent_no_backup_keys = {p["person_key"] for p in risks.get("absent_no_backup", [])}
        # Also projects absent with no backup
        absent_projects_no_backup = [
            p for p in risks.get("absent_owner_projects", [])
            if p.get("owner_key") in absent_no_backup_keys
        ]

        if absent_with_backup:
            lines.append("")
            lines.append("**Nhân sự vắng mặt / có backup**")
            for item in absent_with_backup:
                owner_label = _owner_label(
                    [item["owner_key"]],
                    discord_identity_by_person,
                    [],
                    mention_style=mention_style,
                )
                backup_label = _owner_label(
                    [item["backup_key"]],
                    discord_identity_by_person,
                    [],
                    mention_style="token",
                )
                lines.append(f"- {owner_label} (owner task **{item['task_title']}**) → backup: {backup_label}")

        if risks.get("absent_no_backup"):
            lines.append("")
            lines.append("**Nhân sự vắng mặt / không có backup — cần escalation**")
            for item in risks["absent_no_backup"]:
                lines.append(f"- {item['display_name']} (chưa có backup, cần chỉ định)")

        if risks.get("overloaded_owners"):
            lines.append("")
            lines.append("**Nhân sự quá tải**")
            for item in risks["overloaded_owners"]:
                lines.append(
                    f"- {item['display_name']}: {item['active_projects']} projects, {item['active_tasks']} tasks"
                )

        if risks.get("reduced_bandwidth_with_overdue"):
            lines.append("")
            lines.append("**Nhân sự bandwidth thấp với task overdue**")
            for item in risks["reduced_bandwidth_with_overdue"]:
                pct = int(item.get("bandwidth", 0) * 100)
                lines.append(
                    f"- {item['display_name']} (bandwidth {pct}%): {item['overdue_tasks']} task overdue"
                )

    return "\n".join(lines)



def build_report(*, root: Path | None = None, now: datetime | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    root = root or Path("~/work/py-hbs-ads").expanduser()
    now = now or datetime.now(ICT)
    api_key = load_api_key()
    registry = _read_json(root / "state" / "notion_scrum" / "team_registry.json")
    notion_user_to_person, discord_identity_by_person = _build_people_maps(registry)

    project_pages = _query_all(api_key, "active-projects")
    active_task_pages = _query_all(api_key, "active-tasks")
    ownerless_pages = _query_all(api_key, "ownerless-active-tasks")
    undated_pages = _query_all(api_key, "undated-active-tasks")

    projects = [_compact_project(page, notion_user_to_person) for page in project_pages]
    projects = [project for project in projects if (project.get("status") or "").strip().lower() != "archived"]
    active_project_ids = {project["id"] for project in projects if project.get("id")}
    project_titles = {project["id"]: project.get("title") or project["id"] for project in projects if project.get("id")}

    def keep_task(task: dict[str, Any]) -> bool:
        project_ids = task.get("project_ids") or []
        return not project_ids or any(project_id in active_project_ids for project_id in project_ids)

    tasks = [task for task in (_compact_task_with_people(page, project_titles, notion_user_to_person) for page in active_task_pages) if keep_task(task)]
    ownerless_tasks = [task for task in (_compact_task_with_people(page, project_titles, notion_user_to_person) for page in ownerless_pages) if keep_task(task)]
    undated_tasks = [task for task in (_compact_task_with_people(page, project_titles, notion_user_to_person) for page in undated_pages) if keep_task(task)]

    action_items = []
    today_str = now.date().isoformat()
    for task in tasks:
        due = task.get("due_date")
        if not due:
            continue
        if due <= today_str:
            action_items.append(
                {
                    "title": task.get("title"),
                    "project": (task.get("project_titles") or ["Unknown project"])[0],
                    "due_date": due,
                    "status": task.get("status"),
                    "owner_person_keys": task.get("owner_person_keys") or [],
                    "owner_names": task.get("owner_names") or [],
                    "is_overdue": due < today_str,
                }
            )
    action_items.sort(key=lambda item: (item["due_date"] or "9999-99-99", item["project"], item["title"] or ""))

    analyzed_projects = []
    for project in projects:
        blocks = _fetch_block_texts(api_key, project["id"])
        analyzed_projects.append(analyze_project_hygiene(project, blocks))

    projects_missing_subtasks = [
        {"title": project["title"], "owner_person_keys": project.get("owner_person_keys") or [], "owner_names": project.get("owner_names") or []}
        for project in analyzed_projects
        if project["missing_subtasks"]
    ]
    projects_unclear_content = [
        {"title": project["title"], "owner_person_keys": project.get("owner_person_keys") or [], "owner_names": project.get("owner_names") or []}
        for project in analyzed_projects
        if project["unclear_content"]
    ]
    projects_missing_definition_of_done = [
        {"title": project["title"], "owner_person_keys": project.get("owner_person_keys") or [], "owner_names": project.get("owner_names") or []}
        for project in analyzed_projects
        if project["missing_definition_of_done"]
    ]

    # Optional staffing snapshot
    staffing_snapshot_path = root / "state" / "notion_scrum" / "cache" / "staffing_snapshot.json"
    staffing_risks = None
    if staffing_snapshot_path.exists():
        try:
            snapshot = _read_json(staffing_snapshot_path)
            staffing_risks = staffing_risk.detect_risks(snapshot)
        except Exception as exc:
            import sys
            print(f"WARNING: staffing snapshot load failed ({exc}); skipping staffing sections", file=sys.stderr)

    report = {
        "generated_at_ict": now.strftime("%Y-%m-%d %H:%M ICT"),
        "counts": {
            "active_projects": len(projects),
            "active_tasks": len(tasks),
            "overdue_tasks": sum(1 for item in action_items if item["is_overdue"]),
            "missing_due_date": len(undated_tasks),
            "missing_owner": len(ownerless_tasks),
            "projects_missing_subtasks": len(projects_missing_subtasks),
            "projects_unclear_content": len(projects_unclear_content),
            "projects_missing_definition_of_done": len(projects_missing_definition_of_done),
        },
        "action_items": action_items,
        "ownerless_tasks": ownerless_tasks,
        "undated_tasks": undated_tasks,
        "projects_missing_subtasks": projects_missing_subtasks,
        "projects_unclear_content": projects_unclear_content,
        "projects_missing_definition_of_done": projects_missing_definition_of_done,
        "staffing_risks": staffing_risks,
    }
    return report, discord_identity_by_person



def main() -> int:
    parser = argparse.ArgumentParser(description="Build the HBS creative daily board report.")
    parser.add_argument("--format", choices=["json", "discord"], default="discord")
    parser.add_argument("--mention-style", choices=["discord", "token"], default="discord")
    parser.add_argument("--root", type=Path, default=Path("~/work/py-hbs-ads").expanduser())
    args = parser.parse_args()

    report, discord_identity_by_person = build_report(root=args.root)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_daily_check_message(report, discord_identity_by_person, mention_style=args.mention_style))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
