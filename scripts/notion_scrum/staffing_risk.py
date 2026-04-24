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
    raise NotImplementedError


def compute_routing_recommendation(
    snapshot_person: dict[str, Any],
    people_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute effective follow-up routing recommendation for a snapshot person.

    Wraps people_state_store.effective_followup_target() when people_state is
    provided; falls back to snapshot availability_status when it is None.
    Always sets recommendation_only: True — never modifies Notion ownership.
    """
    raise NotImplementedError
