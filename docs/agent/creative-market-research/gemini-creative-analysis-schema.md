# Gemini Prompt + JSON Schema — Creative Market Research Analysis

## 1. Purpose

This document defines the strict analysis contract for Gemini when analyzing mobile game ad creatives for market research.

Key rule:
- the model must separate **observable evidence** from **interpretation**
- the output must be machine-validated before downstream synthesis

## 2. Prompt design goals

The prompt should force the model to:

1. return JSON only
2. use controlled vocabularies where specified
3. avoid mixing raw observation with strategic conclusions
4. attach evidence references for important claims
5. admit uncertainty explicitly

## 3. Suggested system-style prompt

```text
You are a mobile game ad creative analyst for market research.

Analyze the provided video and return ONLY valid JSON.
Do not use markdown.
Do not include commentary outside the JSON object.

Your job is to separate:
1. observable facts that are directly visible/audible in the creative
2. controlled taxonomy tags
3. higher-order interpretation/hypotheses
4. evidence references and quality flags

Rules:
- If a field is unknown, use null or an explicit unknown enum where defined.
- Do not invent market-wide claims from a single video.
- Keep interpretation conservative.
- Important claims should include timestamp evidence when possible.
- Controlled vocabulary fields must use only the allowed enum values.
```

## 4. Suggested user-style prompt template

```text
Analyze this mobile game ad video for creative market research.

Return JSON matching the required schema.
Focus especially on these analysis dimensions:
- {analysis_focus}

Use the controlled vocabularies exactly where specified.
Mark low confidence explicitly.
```

## 5. Recommended JSON shape

```json
{
  "schema_version": "creative-analysis/v1",
  "asset_ref": "asset_123",
  "observable": {
    "duration_seconds": 0.0,
    "aspect_ratio": "9:16",
    "scene_count_estimate": 0,
    "contains_gameplay": true,
    "gameplay_visibility": "full",
    "creator_presence": "none",
    "character_presence": true,
    "facecam_presence": false,
    "device_frame_presence": false,
    "text_overlay_present": true,
    "text_overlay_summary": ["Level 99", "Download now"],
    "voiceover_type": "human_single",
    "audio_style": "upbeat",
    "cta_present": true,
    "cta_text": "Download now",
    "cta_start_seconds": 21.4,
    "cta_end_seconds": 27.9,
    "offer_present": false,
    "offer_summary": null,
    "visual_notes": "Short factual description only"
  },
  "taxonomy_tags": {
    "hook_type": "fail_then_win",
    "format_type": "gameplay_plus_overlay",
    "core_angle": "progression_reward",
    "emotion_target": "satisfaction",
    "visual_device": ["zoom_highlight", "big_numbers"],
    "proof_type": "on_screen_result",
    "cta_style": "direct_download",
    "audience_hint": ["casual", "idle_players"],
    "funnel_stage_guess": "prospecting"
  },
  "interpretation": {
    "hypothesized_strategy": "Use visible progress and quick wins to promise low-friction reward loops.",
    "why_it_might_work": [
      "Immediate payoff is shown early",
      "The creative reduces cognitive load with obvious progression"
    ],
    "likely_target_player": "Casual idle players who respond to visible progression and upgrade feedback.",
    "competitive_positioning_guess": "Competes on satisfying progression rather than deep narrative.",
    "novelty_assessment": "low"
  },
  "evidence": [
    {
      "type": "hook",
      "start_seconds": 0.0,
      "end_seconds": 2.8,
      "note": "Failure moment appears immediately before recovery and payoff."
    },
    {
      "type": "cta",
      "start_seconds": 21.4,
      "end_seconds": 27.9,
      "note": "Download CTA and store-style framing appear together."
    }
  ],
  "quality": {
    "analysis_confidence": 0.82,
    "needs_human_review": false,
    "failure_modes": [],
    "ocr_confidence": 0.71,
    "timing_confidence": 0.84
  }
}
```

## 6. Controlled vocabularies

## 6.1 `hook_type`
Allowed values:
- `direct_benefit`
- `surprise_reveal`
- `fail_then_win`
- `social_proof`
- `drama_conflict`
- `challenge`
- `curiosity_gap`
- `transformation`
- `before_after`
- `claim_statistic`
- `unknown`

## 6.2 `format_type`
Allowed values:
- `raw_gameplay`
- `gameplay_plus_overlay`
- `ugc_selfie`
- `skit`
- `meme_edit`
- `fake_playable`
- `static_to_motion`
- `ai_avatar_voiceover`
- `compilation`
- `testimonial`
- `unknown`

## 6.3 `core_angle`
Allowed values:
- `progression_reward`
- `skill_mastery`
- `relaxation`
- `chaos_fail`
- `collection_completion`
- `story_drama`
- `social_status`
- `speed_efficiency`
- `customization`
- `survival_tension`
- `unknown`

## 6.4 `gameplay_visibility`
Allowed values:
- `none`
- `partial`
- `full`
- `unknown`

## 6.5 `creator_presence`
Allowed values:
- `none`
- `voice_only`
- `hands_only`
- `facecam`
- `full_body`
- `unknown`

## 6.6 `cta_style`
Allowed values:
- `direct_download`
- `play_now`
- `store_prompt`
- `reward_claim`
- `limited_offer`
- `wishlist`
- `unknown`

## 6.7 `funnel_stage_guess`
Allowed values:
- `prospecting`
- `retargeting`
- `reengagement`
- `unknown`

## 7. JSON Schema draft

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CreativeMarketResearchAnalysis",
  "type": "object",
  "required": [
    "schema_version",
    "observable",
    "taxonomy_tags",
    "interpretation",
    "evidence",
    "quality"
  ],
  "properties": {
    "schema_version": {"type": "string"},
    "asset_ref": {"type": ["string", "null"]},
    "observable": {
      "type": "object",
      "required": [
        "duration_seconds",
        "aspect_ratio",
        "scene_count_estimate",
        "contains_gameplay",
        "gameplay_visibility",
        "creator_presence",
        "text_overlay_present",
        "voiceover_type",
        "audio_style",
        "cta_present",
        "cta_start_seconds",
        "cta_end_seconds",
        "visual_notes"
      ],
      "properties": {
        "duration_seconds": {"type": ["number", "null"]},
        "aspect_ratio": {"type": ["string", "null"]},
        "scene_count_estimate": {"type": ["integer", "null"]},
        "contains_gameplay": {"type": "boolean"},
        "gameplay_visibility": {"type": "string", "enum": ["none", "partial", "full", "unknown"]},
        "creator_presence": {"type": "string", "enum": ["none", "voice_only", "hands_only", "facecam", "full_body", "unknown"]},
        "character_presence": {"type": ["boolean", "null"]},
        "facecam_presence": {"type": ["boolean", "null"]},
        "device_frame_presence": {"type": ["boolean", "null"]},
        "text_overlay_present": {"type": "boolean"},
        "text_overlay_summary": {
          "type": "array",
          "items": {"type": "string"}
        },
        "voiceover_type": {"type": ["string", "null"]},
        "audio_style": {"type": ["string", "null"]},
        "cta_present": {"type": "boolean"},
        "cta_text": {"type": ["string", "null"]},
        "cta_start_seconds": {"type": ["number", "null"]},
        "cta_end_seconds": {"type": ["number", "null"]},
        "offer_present": {"type": ["boolean", "null"]},
        "offer_summary": {"type": ["string", "null"]},
        "visual_notes": {"type": "string"}
      },
      "additionalProperties": false
    },
    "taxonomy_tags": {
      "type": "object",
      "required": [
        "hook_type",
        "format_type",
        "core_angle",
        "emotion_target",
        "cta_style",
        "funnel_stage_guess"
      ],
      "properties": {
        "hook_type": {"type": "string", "enum": ["direct_benefit", "surprise_reveal", "fail_then_win", "social_proof", "drama_conflict", "challenge", "curiosity_gap", "transformation", "before_after", "claim_statistic", "unknown"]},
        "format_type": {"type": "string", "enum": ["raw_gameplay", "gameplay_plus_overlay", "ugc_selfie", "skit", "meme_edit", "fake_playable", "static_to_motion", "ai_avatar_voiceover", "compilation", "testimonial", "unknown"]},
        "core_angle": {"type": "string", "enum": ["progression_reward", "skill_mastery", "relaxation", "chaos_fail", "collection_completion", "story_drama", "social_status", "speed_efficiency", "customization", "survival_tension", "unknown"]},
        "emotion_target": {"type": ["string", "null"]},
        "visual_device": {"type": "array", "items": {"type": "string"}},
        "proof_type": {"type": ["string", "null"]},
        "cta_style": {"type": "string", "enum": ["direct_download", "play_now", "store_prompt", "reward_claim", "limited_offer", "wishlist", "unknown"]},
        "audience_hint": {"type": "array", "items": {"type": "string"}},
        "funnel_stage_guess": {"type": "string", "enum": ["prospecting", "retargeting", "reengagement", "unknown"]}
      },
      "additionalProperties": false
    },
    "interpretation": {
      "type": "object",
      "required": [
        "hypothesized_strategy",
        "why_it_might_work",
        "likely_target_player",
        "competitive_positioning_guess",
        "novelty_assessment"
      ],
      "properties": {
        "hypothesized_strategy": {"type": ["string", "null"]},
        "why_it_might_work": {"type": "array", "items": {"type": "string"}},
        "likely_target_player": {"type": ["string", "null"]},
        "competitive_positioning_guess": {"type": ["string", "null"]},
        "novelty_assessment": {"type": ["string", "null"]}
      },
      "additionalProperties": false
    },
    "evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "start_seconds", "end_seconds", "note"],
        "properties": {
          "type": {"type": "string"},
          "start_seconds": {"type": ["number", "null"]},
          "end_seconds": {"type": ["number", "null"]},
          "note": {"type": "string"}
        },
        "additionalProperties": false
      }
    },
    "quality": {
      "type": "object",
      "required": ["analysis_confidence", "needs_human_review", "failure_modes"],
      "properties": {
        "analysis_confidence": {"type": ["number", "null"]},
        "needs_human_review": {"type": "boolean"},
        "failure_modes": {"type": "array", "items": {"type": "string"}},
        "ocr_confidence": {"type": ["number", "null"]},
        "timing_confidence": {"type": ["number", "null"]}
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

## 8. Validation policy

After generation:

1. parse JSON
2. validate against schema
3. if invalid, return validation errors to the model once for repair
4. if still invalid, store failure record and require review

## 9. Important implementation note

The current `src/hbs_ads/infra/ai/gemini.py` prompt is too narrow for this workflow.
It is useful as a starting point, but this market-research workflow needs a new schema-aware analysis path rather than a simple extension of the old CTA-centric fields.
