from __future__ import annotations

from typing import Any

import people_state_store
from common import utc_now_iso


def detect_risks(
    snapshot: dict[str, Any],
    overload_projects_threshold: int = 3,
    overload_tasks_threshold: int = 8,
) -> dict[str, Any]:
    """Detect all five staffing risk categories from a derived staffing snapshot.

    Returns a structured risk report dict with schema_version, generated_at,
    thresholds, and risks sub-dict containing five categorized lists.
    All output lists are sorted for stable JSON.
    """
    people = snapshot.get("people", {})
    project_effective_owners = snapshot.get("project_effective_owners", {})

    # RISK-01: absent_owner_tasks
    absent_owner_tasks: list[dict[str, Any]] = []
    for person_key, person in people.items():
        if "absent_owner" in person.get("risk_flags", []):
            backup_key = person.get("backup_person_key")
            for task_id, task_title in zip(
                person.get("active_task_ids", []),
                person.get("active_task_titles", []),
            ):
                absent_owner_tasks.append(
                    {
                        "task_id": task_id,
                        "task_title": task_title,
                        "owner_key": person_key,
                        "backup_key": backup_key,
                    }
                )
    absent_owner_tasks.sort(key=lambda x: (x["owner_key"], x["task_id"]))

    # RISK-02: absent_owner_projects
    absent_owner_projects: list[dict[str, Any]] = []
    for project_id, peo in project_effective_owners.items():
        if peo.get("has_absent_owner"):
            for owner_key in peo.get("board_owner_person_keys", []):
                person = people.get(owner_key, {})
                if "absent_owner" in person.get("risk_flags", []):
                    # Resolve project title from person's active_project_titles by index
                    active_project_ids = person.get("active_project_ids", [])
                    active_project_titles = person.get("active_project_titles", [])
                    try:
                        idx = active_project_ids.index(project_id)
                        project_title = active_project_titles[idx]
                    except (ValueError, IndexError):
                        project_title = project_id
                    absent_owner_projects.append(
                        {
                            "project_id": project_id,
                            "project_title": project_title,
                            "owner_key": owner_key,
                        }
                    )
    absent_owner_projects.sort(key=lambda x: (x["owner_key"], x["project_id"]))

    # RISK-03: absent_no_backup
    absent_no_backup: list[dict[str, Any]] = []
    for person_key, person in people.items():
        if "absent_no_backup" in person.get("risk_flags", []):
            absent_no_backup.append(
                {
                    "person_key": person_key,
                    "display_name": person.get("display_name", person_key),
                }
            )
    absent_no_backup.sort(key=lambda x: x["person_key"])

    # RISK-04: overloaded_owners (no check on availability_status or risk_flags)
    overloaded_owners: list[dict[str, Any]] = []
    for person_key, person in people.items():
        if (
            person.get("active_projects", 0) >= overload_projects_threshold
            or person.get("active_tasks", 0) >= overload_tasks_threshold
        ):
            overloaded_owners.append(
                {
                    "person_key": person_key,
                    "display_name": person.get("display_name", person_key),
                    "active_projects": person.get("active_projects", 0),
                    "active_tasks": person.get("active_tasks", 0),
                }
            )
    overloaded_owners.sort(key=lambda x: x["person_key"])

    # RISK-05: reduced_bandwidth_with_overdue
    reduced_bandwidth_with_overdue: list[dict[str, Any]] = []
    for person_key, person in people.items():
        if person.get("bandwidth") in {"reduced", "limited"} and person.get("overdue_tasks", 0) > 0:
            reduced_bandwidth_with_overdue.append(
                {
                    "person_key": person_key,
                    "display_name": person.get("display_name", person_key),
                    "bandwidth": person.get("bandwidth"),
                    "overdue_tasks": person.get("overdue_tasks", 0),
                }
            )
    reduced_bandwidth_with_overdue.sort(key=lambda x: x["person_key"])

    return {
        "schema_version": "1.0",
        "generated_at": utc_now_iso(),
        "thresholds": {
            "overload_projects": overload_projects_threshold,
            "overload_tasks": overload_tasks_threshold,
        },
        "risks": {
            "absent_owner_tasks": absent_owner_tasks,
            "absent_owner_projects": absent_owner_projects,
            "absent_no_backup": absent_no_backup,
            "overloaded_owners": overloaded_owners,
            "reduced_bandwidth_with_overdue": reduced_bandwidth_with_overdue,
        },
    }


def compute_routing_recommendation(
    snapshot_person: dict[str, Any],
    people_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute effective follow-up routing recommendation for a snapshot person.

    Wraps people_state_store.effective_followup_target() when people_state is
    provided; falls back to snapshot availability_status when it is None.
    Always sets recommendation_only: True — never modifies Notion ownership.
    """
    person_key = snapshot_person["canonical_person_key"]

    if people_state is not None:
        target_key, routing_reason = people_state_store.effective_followup_target(
            people_state, person_key
        )
    else:
        status = snapshot_person.get("availability_status", "unknown")
        backup = snapshot_person.get("backup_person_key")
        if status == "active":
            target_key, routing_reason = person_key, "owner_active"
        elif status in {"leave", "ooo"}:
            if backup:
                target_key, routing_reason = backup, "owner_absent_backup_used"
            else:
                target_key, routing_reason = person_key, "escalation_needed"
        else:
            target_key, routing_reason = person_key, "unknown"

    bandwidth = snapshot_person.get("bandwidth", "unknown")
    note = None
    if bandwidth in {"reduced", "limited"}:
        note = f"Owner has {bandwidth} bandwidth; include backup/lead for higher-urgency items"

    return {
        "target_person_key": target_key,
        "routing_reason": routing_reason,
        "recommendation_only": True,
        "note": note,
    }
