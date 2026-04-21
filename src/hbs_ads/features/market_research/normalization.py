from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from hbs_ads.features.market_research.models import AdCandidate


_PLATFORM_ALIASES: dict[str, str] = {
    "fb": "meta",
    "facebook": "meta",
    "ig": "meta",
    "instagram": "meta",
    "tt": "tiktok",
    "tik_tok": "tiktok",
    "yt": "youtube",
    "youtube_shorts": "youtube",
    "goog": "google",
    "google_uac": "google",
}


def normalize_platform(raw: str) -> str:
    key = raw.strip().lower()
    return _PLATFORM_ALIASES.get(key, key)


def normalize_date(raw: str) -> str:
    if not raw:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return raw


def build_dedupe_key(candidate: AdCandidate) -> str:
    parts = [
        candidate.source.lower(),
        candidate.source_record_id.lower(),
        candidate.asset_url.lower(),
    ]
    combined = "|".join(p for p in parts if p)
    if not combined:
        combined = candidate.candidate_id
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def assign_candidate_id(run_id: str, source: str, source_record_id: str, index: int) -> str:
    raw = f"{run_id}|{source}|{source_record_id}|{index}"
    return "cand_" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def normalize_raw_record(run_id: str, query_id: str, raw: dict[str, Any], index: int) -> AdCandidate:
    source = normalize_platform(str(raw.get("source", "") or ""))
    source_record_id = str(raw.get("source_record_id", "") or raw.get("id", "") or "")
    candidate_id = assign_candidate_id(run_id, source, source_record_id, index)

    candidate = AdCandidate(
        candidate_id=candidate_id,
        run_id=run_id,
        query_id=query_id,
        source=source,
        source_record_id=source_record_id,
        source_url=str(raw.get("source_url", "") or ""),
        app_name=str(raw.get("app_name", "") or ""),
        publisher_name=str(raw.get("publisher_name", "") or ""),
        geo=str(raw.get("geo", "") or "").upper(),
        platform=normalize_platform(str(raw.get("platform", "") or source)),
        first_seen_at=normalize_date(str(raw.get("first_seen_at", "") or "")),
        last_seen_at=normalize_date(str(raw.get("last_seen_at", "") or "")),
        asset_url=str(raw.get("asset_url", "") or ""),
        thumbnail_url=str(raw.get("thumbnail_url", "") or ""),
        landing_url=str(raw.get("landing_url", "") or ""),
        raw_payload=raw,
        normalized_status="normalized",
    )
    candidate.dedupe_key = build_dedupe_key(candidate)
    return candidate


def normalize_candidates(
    run_id: str,
    query_id: str,
    raw_records: list[dict[str, Any]],
) -> list[AdCandidate]:
    return [normalize_raw_record(run_id, query_id, rec, i) for i, rec in enumerate(raw_records)]
