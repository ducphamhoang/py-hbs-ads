#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from board_config import DEFAULT_BOARD_CONFIG, load as load_board_config
from common import DEFAULT_ROOT, load_api_key, notion_request, save_json, utc_now_iso
from result_contracts import build_result

DEFAULT_CACHE_DIR = DEFAULT_ROOT / "state" / "notion_scrum" / "cache"
DEFAULT_BOARD_CACHE = DEFAULT_CACHE_DIR / "board_snapshot.json"
DEFAULT_PROJECTS_DATA_SOURCE_ID = DEFAULT_BOARD_CONFIG["projects_data_source_id"]
DEFAULT_TASKS_DATA_SOURCE_ID = DEFAULT_BOARD_CONFIG["tasks_data_source_id"]


def _text_value(prop: dict[str, Any] | None, key: str) -> str | None:
    if not prop:
        return None
    items = prop.get(key) or []
    text = "".join(part.get("plain_text", "") for part in items).strip()
    return text or None


def _people_value(prop: dict[str, Any] | None) -> list[dict[str, str | None]]:
    if not prop:
        return []
    return [
        {
            "id": person.get("id"),
            "name": person.get("name") or ((person.get("person") or {}).get("email")),
        }
        for person in (prop.get("people") or [])
    ]


def _relation_ids(prop: dict[str, Any] | None) -> list[str]:
    if not prop:
        return []
    return [item.get("id") for item in (prop.get("relation") or []) if item.get("id")]


def _status_name(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    return (prop.get("status") or {}).get("name")


def _date_start(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    return ((prop.get("date") or {}).get("start"))


def _rich_text(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    text = "".join(part.get("plain_text", "") for part in (prop.get("rich_text") or [])).strip()
    return text or None


def _compact_project(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties") or {}
    owners = _people_value(props.get("Project lead") or props.get("Assignee") or props.get("Owner"))
    return {
        "id": page.get("id"),
        "title": _text_value(props.get("Project name") or props.get("Name"), "title"),
        "status": _status_name(props.get("Status")),
        "start_date": _date_start(props.get("Start date")),
        "end_date": _date_start(props.get("End date")),
        "owner_ids": [item.get("id") for item in owners if item.get("id")],
        "owner_names": [item.get("name") for item in owners if item.get("name")],
        "url": page.get("url"),
        "last_edited_time": page.get("last_edited_time"),
    }


def _compact_task(page: dict[str, Any], project_titles: dict[str, str]) -> dict[str, Any]:
    props = page.get("properties") or {}
    owners = _people_value(props.get("Assignee") or props.get("Owner"))
    project_ids = _relation_ids(props.get("Projects 1") or props.get("Project") or props.get("Projects"))
    return {
        "id": page.get("id"),
        "title": _text_value(props.get("Task name") or props.get("Name"), "title"),
        "status": _status_name(props.get("Status")),
        "due_date": _date_start(props.get("Due date")),
        "owner_ids": [item.get("id") for item in owners if item.get("id")],
        "owner_names": [item.get("name") for item in owners if item.get("name")],
        "project_ids": project_ids,
        "project_titles": [project_titles.get(project_id, project_id) for project_id in project_ids],
        "blocked_reason": _rich_text(props.get("Blocked reason")),
        "url": page.get("url"),
        "last_edited_time": page.get("last_edited_time"),
    }


def _title_index(records: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for record_id, record in records.items():
        title = record.get("title")
        if not title:
            continue
        index.setdefault(title, []).append(record_id)
    return index


def build_snapshot(
    *,
    project_pages: list[dict[str, Any]],
    task_pages: list[dict[str, Any]],
    fetched_at: str,
    projects_data_source_id: str,
    tasks_data_source_id: str,
) -> dict[str, Any]:
    projects = [_compact_project(page) for page in project_pages]
    projects_by_id = {project["id"]: project for project in projects if project.get("id")}
    project_titles = {
        project_id: project.get("title") or project_id
        for project_id, project in projects_by_id.items()
    }
    tasks = [_compact_task(page, project_titles) for page in task_pages]
    tasks_by_id = {task["id"]: task for task in tasks if task.get("id")}

    return {
        "schema_version": "1.0",
        "meta": {
            "generated_at": fetched_at,
            "projects_data_source_id": projects_data_source_id,
            "tasks_data_source_id": tasks_data_source_id,
            "project_count": len(projects_by_id),
            "task_count": len(tasks_by_id),
        },
        "indexes": {
            "projects_by_title": _title_index(projects_by_id),
            "tasks_by_title": _title_index(tasks_by_id),
        },
        "records": {
            "projects": projects_by_id,
            "tasks": tasks_by_id,
        },
    }


def load_snapshot(cache_path: Path = DEFAULT_BOARD_CACHE) -> dict[str, Any]:
    if not cache_path.exists():
        return {}
    text = cache_path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def snapshot_age_seconds(snapshot: dict[str, Any], *, now_iso: str | None = None) -> float | None:
    generated_at = ((snapshot.get("meta") or {}).get("generated_at"))
    generated = _parse_iso8601(generated_at)
    if generated is None:
        return None
    now = _parse_iso8601(now_iso) if now_iso else datetime.now(timezone.utc)
    if now is None:
        return None
    return max((now - generated).total_seconds(), 0.0)


def is_snapshot_fresh(snapshot: dict[str, Any], *, max_age_seconds: int, now_iso: str | None = None) -> bool:
    age = snapshot_age_seconds(snapshot, now_iso=now_iso)
    if age is None:
        return False
    return age <= max_age_seconds


def _filter_candidate_ids(snapshot: dict[str, Any], *, kind: str, candidate_ids: list[str], project_title: str | None) -> list[str]:
    if kind != "tasks" or not project_title:
        return candidate_ids
    filtered: list[str] = []
    for candidate_id in candidate_ids:
        record = get_record(snapshot, kind="tasks", record_id=candidate_id) or {}
        project_titles = record.get("project_titles") or []
        if project_title in project_titles:
            filtered.append(candidate_id)
    return filtered


def _compact_live_page(kind: str, page: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    if kind == "projects":
        return _compact_project(page)
    if kind == "tasks":
        project_titles = {
            project_id: project.get("title") or project_id
            for project_id, project in (((snapshot.get("records") or {}).get("projects") or {}).items())
        }
        return _compact_task(page, project_titles)
    raise KeyError(f"Unknown cache kind: {kind}")


def resolve_target(
    *,
    snapshot: dict[str, Any],
    kind: str,
    title: str,
    project_title: str | None = None,
    mode: str = "auto",
    max_cache_age_seconds: int = 900,
    now_iso: str | None = None,
) -> dict[str, Any]:
    if kind not in {"projects", "tasks"}:
        raise KeyError(f"Unknown cache kind: {kind}")
    if mode not in {"auto", "safe", "fast"}:
        raise KeyError(f"Unknown resolve mode: {mode}")

    candidate_ids = lookup_exact_title(snapshot, kind=kind, title=title)
    candidate_ids = _filter_candidate_ids(snapshot, kind=kind, candidate_ids=candidate_ids, project_title=project_title)
    age_seconds = snapshot_age_seconds(snapshot, now_iso=now_iso)
    is_fresh = is_snapshot_fresh(snapshot, max_age_seconds=max_cache_age_seconds, now_iso=now_iso)

    if not candidate_ids:
        return build_result(
            ok=False,
            action_taken="target_not_found",
            errors=[f"No cached {kind[:-1] if kind.endswith('s') else kind} matched title {title!r}"],
            data={
                "kind": kind,
                "title": title,
                "project_title": project_title,
                "candidate_ids": [],
                "cache_age_seconds": age_seconds,
                "cache_is_fresh": is_fresh,
            },
        )

    if len(candidate_ids) != 1:
        candidate_records = _candidate_summaries(snapshot, kind=kind, candidate_ids=candidate_ids)
        return build_result(
            ok=False,
            action_taken="target_ambiguous",
            errors=[f"Cached title lookup for {title!r} matched {len(candidate_ids)} {kind}; need more context"],
            data={
                "kind": kind,
                "title": title,
                "project_title": project_title,
                "candidate_ids": candidate_ids,
                "candidate_records": candidate_records,
                "ambiguity_message": format_ambiguity_message(kind=kind, title=title, candidate_records=candidate_records),
                "cache_age_seconds": age_seconds,
                "cache_is_fresh": is_fresh,
            },
        )

    resolved_id = candidate_ids[0]
    cached_record = get_record(snapshot, kind=kind, record_id=resolved_id) or {}

    if mode == "fast" and not is_fresh:
        return build_result(
            ok=False,
            action_taken="cache_stale",
            errors=[f"Cached snapshot is stale ({age_seconds:.0f}s old); fast mode refuses to resolve without live revalidation"],
            data={
                "kind": kind,
                "title": title,
                "project_title": project_title,
                "candidate_ids": candidate_ids,
                "resolved_id": resolved_id,
                "cache_age_seconds": age_seconds,
                "cache_is_fresh": is_fresh,
                "used_live_revalidation": False,
                "mode": mode,
            },
        )

    should_use_fast_path = mode == "fast" or (mode == "auto" and is_fresh)
    if should_use_fast_path:
        return build_result(
            ok=True,
            action_taken="target_resolved_from_cache",
            data={
                "kind": kind,
                "title": title,
                "project_title": project_title,
                "candidate_ids": candidate_ids,
                "resolved_id": resolved_id,
                "record": cached_record,
                "cache_age_seconds": age_seconds,
                "cache_is_fresh": is_fresh,
                "used_live_revalidation": False,
                "mode": mode,
            },
        )

    try:
        api_key = load_api_key()
        page = notion_request(api_key, "GET", f"https://api.notion.com/v1/pages/{resolved_id}")
    except Exception as exc:
        return build_result(
            ok=False,
            action_taken="live_revalidation_failed",
            errors=[f"live revalidation failed for {resolved_id}: {exc}"],
            data={
                "kind": kind,
                "title": title,
                "project_title": project_title,
                "candidate_ids": candidate_ids,
                "resolved_id": resolved_id,
                "record": cached_record,
                "cache_age_seconds": age_seconds,
                "cache_is_fresh": is_fresh,
                "used_live_revalidation": True,
                "mode": mode,
            },
        )
    live_record = _compact_live_page(kind, page, snapshot)
    if live_record.get("title") != title:
        return build_result(
            ok=False,
            action_taken="live_revalidation_failed",
            errors=[f"Live page title mismatch for {resolved_id}: expected {title!r}, got {live_record.get('title')!r}"],
            data={
                "kind": kind,
                "title": title,
                "project_title": project_title,
                "candidate_ids": candidate_ids,
                "resolved_id": resolved_id,
                "record": live_record,
                "cache_age_seconds": age_seconds,
                "cache_is_fresh": is_fresh,
                "used_live_revalidation": True,
                "mode": mode,
            },
        )
    if kind == "tasks" and project_title and project_title not in (live_record.get("project_titles") or []):
        return build_result(
            ok=False,
            action_taken="live_revalidation_failed",
            errors=[f"Live task {resolved_id} is no longer linked to project {project_title!r}"],
            data={
                "kind": kind,
                "title": title,
                "project_title": project_title,
                "candidate_ids": candidate_ids,
                "resolved_id": resolved_id,
                "record": live_record,
                "cache_age_seconds": age_seconds,
                "cache_is_fresh": is_fresh,
                "used_live_revalidation": True,
                "mode": mode,
            },
        )
    return build_result(
        ok=True,
        action_taken="target_resolved_after_live_check",
        data={
            "kind": kind,
            "title": title,
            "project_title": project_title,
            "candidate_ids": candidate_ids,
            "resolved_id": resolved_id,
            "record": live_record,
            "cache_age_seconds": age_seconds,
            "cache_is_fresh": is_fresh,
            "used_live_revalidation": True,
            "mode": mode,
        },
    )


def lookup_exact_title(snapshot: dict[str, Any], *, kind: str, title: str) -> list[str]:
    if kind not in {"projects", "tasks"}:
        raise KeyError(f"Unknown cache kind: {kind}")
    index_key = f"{kind}_by_title"
    return list((((snapshot.get("indexes") or {}).get(index_key) or {}).get(title) or []))


def get_record(snapshot: dict[str, Any], *, kind: str, record_id: str) -> dict[str, Any] | None:
    if kind not in {"projects", "tasks"}:
        raise KeyError(f"Unknown cache kind: {kind}")
    return (((snapshot.get("records") or {}).get(kind) or {}).get(record_id))


def _candidate_summaries(snapshot: dict[str, Any], *, kind: str, candidate_ids: list[str]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        record = get_record(snapshot, kind=kind, record_id=candidate_id) or {}
        summaries.append({
            "id": candidate_id,
            "title": record.get("title"),
            "status": record.get("status"),
            "due_date": record.get("due_date"),
            "project_titles": list(record.get("project_titles") or []),
            "owner_names": list(record.get("owner_names") or []),
        })
    return summaries


def format_ambiguity_message(*, kind: str, title: str, candidate_records: list[dict[str, Any]]) -> str:
    if not candidate_records:
        return f"{kind[:-1].capitalize()} {title!r} is ambiguous."
    lines = [f"{kind[:-1].capitalize()} {title!r} đang match nhiều rows. Chọn 1 trong các candidate sau:"]
    for idx, record in enumerate(candidate_records, start=1):
        project_part = ", ".join(record.get("project_titles") or []) or "không link project"
        status = record.get("status") or "(no status)"
        due_date = record.get("due_date") or "no due date"
        owners = ", ".join(record.get("owner_names") or []) or "no owner"
        lines.append(f"{idx}. id={record.get('id')} | project={project_part} | status={status} | due={due_date} | owner={owners}")
    return "\n".join(lines)


def _query_all_pages(*, api_key: str, data_source_id: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        payload = notion_request(
            api_key,
            "POST",
            f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
            body,
        )
        pages.extend(payload.get("results") or [])
        has_more = bool(payload.get("has_more"))
        if not has_more:
            break
        cursor = payload.get("next_cursor")
        if not cursor:
            raise RuntimeError(f"incomplete pagination for data source {data_source_id}: has_more=true but next_cursor missing")
    return pages


def sync_cache(
    *,
    cache_path: Path = DEFAULT_BOARD_CACHE,
    projects_data_source_id: str | None = None,
    tasks_data_source_id: str | None = None,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    fetched_at = fetched_at or utc_now_iso()
    board_config = load_board_config()
    projects_data_source_id = projects_data_source_id or board_config["projects_data_source_id"]
    tasks_data_source_id = tasks_data_source_id or board_config["tasks_data_source_id"]
    try:
        api_key = load_api_key()
        project_pages = _query_all_pages(api_key=api_key, data_source_id=projects_data_source_id)
        task_pages = _query_all_pages(api_key=api_key, data_source_id=tasks_data_source_id)
        snapshot = build_snapshot(
            project_pages=project_pages,
            task_pages=task_pages,
            fetched_at=fetched_at,
            projects_data_source_id=projects_data_source_id,
            tasks_data_source_id=tasks_data_source_id,
        )
        save_json(cache_path, snapshot)
    except Exception as exc:
        return build_result(
            ok=False,
            action_taken="cache_sync_failed",
            errors=[str(exc)],
            data={
                "cache_path": str(cache_path),
                "generated_at": fetched_at,
            },
        )
    return build_result(
        ok=True,
        action_taken="cache_synced",
        data={
            "cache_path": str(cache_path),
            "project_count": snapshot["meta"]["project_count"],
            "task_count": snapshot["meta"]["task_count"],
            "generated_at": fetched_at,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync a local Notion board cache for Projects + Tasks Tracker")
    parser.add_argument("--cache", type=Path, default=DEFAULT_BOARD_CACHE)
    parser.add_argument("--projects-data-source-id", default=DEFAULT_PROJECTS_DATA_SOURCE_ID)
    parser.add_argument("--tasks-data-source-id", default=DEFAULT_TASKS_DATA_SOURCE_ID)
    args = parser.parse_args()
    result = sync_cache(
        cache_path=args.cache,
        projects_data_source_id=args.projects_data_source_id,
        tasks_data_source_id=args.tasks_data_source_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
