from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import staffing_risk  # noqa: E402


# ---------------------------------------------------------------------------
# Inline helpers (no @pytest.fixture decorators — inline pattern per project)
# ---------------------------------------------------------------------------


def _snapshot_with_absent_owner_task() -> dict:
    """Snapshot with alice on leave; she owns task-1 and proj-1."""
    return {
        "people": {
            "alice": {
                "canonical_person_key": "alice",
                "display_name": "Alice",
                "availability_status": "leave",
                "backup_person_key": "bob",
                "active_project_ids": ["proj-1"],
                "active_project_titles": ["Alpha"],
                "active_task_ids": ["task-1"],
                "active_task_titles": ["Task One"],
                "active_projects": 1,
                "active_tasks": 1,
                "overdue_tasks": 0,
                "bandwidth": "unknown",
                "risk_flags": ["absent_owner"],
            }
        },
        "project_effective_owners": {
            "proj-1": {
                "project_id": "proj-1",
                "project_title": "Alpha",
                "has_absent_owner": True,
                "board_owner_person_keys": ["alice"],
            }
        },
    }


def _snapshot_with_overloaded_person(active_projects: int, active_tasks: int) -> dict:
    """Snapshot with charlie at given project/task counts."""
    return {
        "people": {
            "charlie": {
                "canonical_person_key": "charlie",
                "display_name": "Charlie",
                "availability_status": "active",
                "backup_person_key": None,
                "active_project_ids": [f"proj-{i}" for i in range(active_projects)],
                "active_project_titles": [f"Proj {i}" for i in range(active_projects)],
                "active_task_ids": [f"task-{i}" for i in range(active_tasks)],
                "active_task_titles": [f"Task {i}" for i in range(active_tasks)],
                "active_projects": active_projects,
                "active_tasks": active_tasks,
                "overdue_tasks": 0,
                "bandwidth": "unknown",
                "risk_flags": [],
            }
        },
        "project_effective_owners": {},
    }


def _snapshot_with_reduced_bandwidth(bandwidth: str, overdue_tasks: int) -> dict:
    """Snapshot with dana at given bandwidth and overdue task count."""
    return {
        "people": {
            "dana": {
                "canonical_person_key": "dana",
                "display_name": "Dana",
                "availability_status": "active",
                "backup_person_key": None,
                "active_project_ids": [],
                "active_project_titles": [],
                "active_task_ids": [],
                "active_task_titles": [],
                "active_projects": 0,
                "active_tasks": 0,
                "overdue_tasks": overdue_tasks,
                "bandwidth": bandwidth,
                "risk_flags": [],
            }
        },
        "project_effective_owners": {},
    }


def _snapshot_person_dict(
    status: str,
    backup_key: str | None = None,
    bandwidth: str = "unknown",
) -> dict:
    """Minimal person dict for compute_routing_recommendation tests."""
    return {
        "canonical_person_key": "person-x",
        "display_name": "Person X",
        "availability_status": status,
        "backup_person_key": backup_key,
        "active_project_ids": [],
        "active_project_titles": [],
        "active_task_ids": [],
        "active_task_titles": [],
        "active_projects": 0,
        "active_tasks": 0,
        "overdue_tasks": 0,
        "bandwidth": bandwidth,
        "risk_flags": [],
    }


# ---------------------------------------------------------------------------
# Tests — RISK-01..05 and ROUT-01..04
# ---------------------------------------------------------------------------


def test_risk_01_absent_owner_tasks() -> None:
    snapshot = _snapshot_with_absent_owner_task()
    result = staffing_risk.detect_risks(snapshot)
    tasks = result["risks"]["absent_owner_tasks"]
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == "task-1"
    assert tasks[0]["owner_key"] == "alice"
    assert tasks[0]["backup_key"] == "bob"


def test_risk_02_absent_owner_projects() -> None:
    snapshot = _snapshot_with_absent_owner_task()
    result = staffing_risk.detect_risks(snapshot)
    projects = result["risks"]["absent_owner_projects"]
    assert len(projects) == 1
    assert projects[0]["project_id"] == "proj-1"
    assert projects[0]["project_title"] == "Alpha"
    assert projects[0]["owner_key"] == "alice"


def test_risk_03_absent_no_backup() -> None:
    snapshot = {
        "people": {
            "eve": {
                "canonical_person_key": "eve",
                "display_name": "Eve",
                "availability_status": "leave",
                "backup_person_key": None,
                "active_project_ids": [],
                "active_project_titles": [],
                "active_task_ids": [],
                "active_task_titles": [],
                "active_projects": 0,
                "active_tasks": 0,
                "overdue_tasks": 0,
                "bandwidth": "unknown",
                "risk_flags": ["absent_owner", "absent_no_backup"],
            }
        },
        "project_effective_owners": {},
    }
    result = staffing_risk.detect_risks(snapshot)
    no_backup = result["risks"]["absent_no_backup"]
    assert any(r["person_key"] == "eve" for r in no_backup)


def test_risk_04_overloaded_owners() -> None:
    # projects threshold hit (active_projects=4 >= default 3)
    s1 = _snapshot_with_overloaded_person(active_projects=4, active_tasks=3)
    r1 = staffing_risk.detect_risks(s1)
    assert any(r["person_key"] == "charlie" for r in r1["risks"]["overloaded_owners"])
    # tasks threshold hit (active_tasks=9 >= default 8)
    s2 = _snapshot_with_overloaded_person(active_projects=2, active_tasks=9)
    r2 = staffing_risk.detect_risks(s2)
    assert any(r["person_key"] == "charlie" for r in r2["risks"]["overloaded_owners"])
    # below both thresholds — should NOT appear
    s3 = _snapshot_with_overloaded_person(active_projects=2, active_tasks=5)
    r3 = staffing_risk.detect_risks(s3)
    assert not any(r["person_key"] == "charlie" for r in r3["risks"]["overloaded_owners"])


def test_risk_04_threshold_override() -> None:
    snapshot = _snapshot_with_overloaded_person(active_projects=2, active_tasks=5)
    # Default thresholds: NOT overloaded
    result = staffing_risk.detect_risks(snapshot)
    assert not any(r["person_key"] == "charlie" for r in result["risks"]["overloaded_owners"])
    # Custom lower threshold: IS overloaded
    result2 = staffing_risk.detect_risks(snapshot, overload_projects_threshold=2)
    assert any(r["person_key"] == "charlie" for r in result2["risks"]["overloaded_owners"])


def test_risk_05_reduced_bandwidth_overdue() -> None:
    # reduced + overdue: appears
    s1 = _snapshot_with_reduced_bandwidth(bandwidth="reduced", overdue_tasks=1)
    r1 = staffing_risk.detect_risks(s1)
    assert any(r["person_key"] == "dana" for r in r1["risks"]["reduced_bandwidth_with_overdue"])
    # full bandwidth + overdue: does NOT appear
    s2 = _snapshot_with_reduced_bandwidth(bandwidth="full", overdue_tasks=1)
    r2 = staffing_risk.detect_risks(s2)
    assert not any(r["person_key"] == "dana" for r in r2["risks"]["reduced_bandwidth_with_overdue"])
    # limited + overdue=0: does NOT appear
    s3 = _snapshot_with_reduced_bandwidth(bandwidth="limited", overdue_tasks=0)
    r3 = staffing_risk.detect_risks(s3)
    assert not any(r["person_key"] == "dana" for r in r3["risks"]["reduced_bandwidth_with_overdue"])


def test_rout_01_active_owner() -> None:
    person = _snapshot_person_dict(status="active")
    result = staffing_risk.compute_routing_recommendation(person, people_state=None)
    assert result["target_person_key"] == "person-x"
    assert result["routing_reason"] == "owner_active"
    assert result["recommendation_only"] is True


def test_rout_02_backup_routing() -> None:
    person = _snapshot_person_dict(status="leave", backup_key="bob")
    result = staffing_risk.compute_routing_recommendation(person, people_state=None)
    assert result["target_person_key"] == "bob"
    assert result["routing_reason"] == "owner_absent_backup_used"
    assert result["recommendation_only"] is True


def test_rout_03_escalation_needed() -> None:
    person = _snapshot_person_dict(status="ooo", backup_key=None)
    result = staffing_risk.compute_routing_recommendation(person, people_state=None)
    assert result["routing_reason"] == "escalation_needed"
    assert result["recommendation_only"] is True


def test_rout_04_recommendation_only() -> None:
    for status in ("active", "leave", "ooo", "partial", "unknown"):
        person = _snapshot_person_dict(status=status, backup_key=None)
        result = staffing_risk.compute_routing_recommendation(person, people_state=None)
        assert result["recommendation_only"] is True, (
            f"recommendation_only not True for status={status}"
        )
