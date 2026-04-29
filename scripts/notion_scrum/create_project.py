#!/usr/bin/env python3
"""Create a new project in the Projects database with optional initial task."""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

NOTION_VERSION = "2025-09-03"


def load_api_key() -> str:
    key = os.getenv("NOTION_API_KEY", "").strip()
    if key:
        return key
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            env_key, _, env_value = line.partition("=")
            if env_key.strip() == "NOTION_API_KEY":
                return env_value.strip().strip('"\'').split("#")[0].strip()
    raise SystemExit("NOTION_API_KEY not found")


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


def create_project(
    api_key: str,
    database_id: str,
    project_name: str,
    brief: str | None = None,
    status: str = "In progress",
    owner_notion_email: str | None = None,
) -> dict[str, Any]:
    properties = {
        "Project name": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": project_name},
                }
            ]
        },
        "Status": {
            "status": {"name": status},
        },
    }
    
    # Owner assignment skipped - property name may differ; can be added manually
    
    page_data = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    
    if brief:
        page_data["children"] = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": brief},
                        }
                    ]
                },
            }
        ]
    
    return notion_request(api_key, "POST", f"https://api.notion.com/v1/pages", page_data)


def create_task(
    api_key: str,
    database_id: str,
    task_name: str,
    project_id: str,
    brief: str | None = None,
    status: str = "To do",
) -> dict[str, Any]:
    properties = {
        "Task name": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": task_name},
                }
            ]
        },
        "Status": {
            "status": {"name": status},
        },
        "Projects": {
            "relation": [{"id": project_id}]
        },
    }
    
    page_data = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    
    if brief:
        page_data["children"] = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": brief},
                        }
                    ]
                },
            }
        ]
    
    return notion_request(api_key, "POST", f"https://api.notion.com/v1/pages", page_data)


def main() -> None:
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Create a new project in Notion")
    parser.add_argument("--project-name", required=True, help="Project title")
    parser.add_argument("--project-brief", help="Project brief/description")
    parser.add_argument("--project-status", default="In progress", help="Project status")
    parser.add_argument("--project-owner-email", help="Owner's Notion email")
    parser.add_argument("--task-name", help="Initial task name (optional)")
    parser.add_argument("--task-brief", help="Initial task brief (optional)")
    parser.add_argument("--task-status", default="To do", help="Initial task status")
    parser.add_argument("--projects-db-id", default="2e945d07-72af-8165-b4da-ccb3ef6a0a97", help="Projects database ID")
    parser.add_argument("--tasks-db-id", default="2e945d07-72af-81dd-821a-000b082e6e95", help="Tasks database ID")
    parser.add_argument("--execute", action="store_true", help="Actually create (default: dry-run)")
    args = parser.parse_args()
    
    api_key = load_api_key()
    
    result = {"ok": True, "data": {}}
    
    if args.execute:
        # Create project
        project = create_project(
            api_key=api_key,
            database_id=args.projects_db_id,
            project_name=args.project_name,
            brief=args.project_brief,
            status=args.project_status,
            owner_notion_email=args.project_owner_email,
        )
        project_id = project["id"]
        project_url = project.get("url", "")
        
        result["data"]["project"] = {
            "id": project_id,
            "name": args.project_name,
            "url": project_url,
        }
        
        # Create task if specified
        if args.task_name:
            task = create_task(
                api_key=api_key,
                database_id=args.tasks_db_id,
                task_name=args.task_name,
                project_id=project_id,
                brief=args.task_brief,
                status=args.task_status,
            )
            result["data"]["task"] = {
                "id": task["id"],
                "name": args.task_name,
                "url": task.get("url", ""),
            }
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "ok": True,
            "dry_run": True,
            "would_create": {
                "project": {
                    "name": args.project_name,
                    "brief": args.project_brief,
                    "status": args.project_status,
                    "owner_email": args.project_owner_email,
                },
                "task": {
                    "name": args.task_name,
                    "brief": args.task_brief,
                    "status": args.task_status,
                } if args.task_name else None,
            }
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
