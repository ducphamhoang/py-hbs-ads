from __future__ import annotations

HOOK_TYPES: frozenset[str] = frozenset({
    "direct_benefit",
    "surprise_reveal",
    "fail_then_win",
    "social_proof",
    "drama_conflict",
    "challenge",
    "curiosity_gap",
    "transformation",
    "before_after",
    "claim_statistic",
    "unknown",
})

FORMAT_TYPES: frozenset[str] = frozenset({
    "raw_gameplay",
    "gameplay_plus_overlay",
    "ugc_selfie",
    "skit",
    "meme_edit",
    "fake_playable",
    "static_to_motion",
    "ai_avatar_voiceover",
    "compilation",
    "testimonial",
    "unknown",
})

CORE_ANGLES: frozenset[str] = frozenset({
    "progression_reward",
    "skill_mastery",
    "relaxation",
    "chaos_fail",
    "collection_completion",
    "story_drama",
    "social_status",
    "speed_efficiency",
    "customization",
    "survival_tension",
    "unknown",
})

GAMEPLAY_VISIBILITY: frozenset[str] = frozenset({"none", "partial", "full", "unknown"})

CREATOR_PRESENCE: frozenset[str] = frozenset({
    "none",
    "voice_only",
    "hands_only",
    "facecam",
    "full_body",
    "unknown",
})

CTA_STYLES: frozenset[str] = frozenset({
    "direct_download",
    "play_now",
    "store_prompt",
    "reward_claim",
    "limited_offer",
    "wishlist",
    "unknown",
})

FUNNEL_STAGES: frozenset[str] = frozenset({"prospecting", "retargeting", "reengagement", "unknown"})

REVIEW_DECISIONS: frozenset[str] = frozenset({
    "approve",
    "approve_with_edits",
    "reject",
    "defer_for_more_evidence",
})

INSIGHT_TYPES: frozenset[str] = frozenset({
    "pattern",
    "gap",
    "trend",
    "competitor_tactic",
    "experiment_opportunity",
})

CONFIDENCE_LEVELS: frozenset[str] = frozenset({"low", "medium", "high"})

ANALYSIS_SCHEMA_VERSION = "creative-analysis/v1"


def all_controlled_vocab() -> dict[str, frozenset[str]]:
    return {
        "hook_type": HOOK_TYPES,
        "format_type": FORMAT_TYPES,
        "core_angle": CORE_ANGLES,
        "gameplay_visibility": GAMEPLAY_VISIBILITY,
        "creator_presence": CREATOR_PRESENCE,
        "cta_style": CTA_STYLES,
        "funnel_stage_guess": FUNNEL_STAGES,
    }
