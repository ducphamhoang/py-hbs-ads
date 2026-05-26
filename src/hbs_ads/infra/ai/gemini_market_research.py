from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hbs_ads.app.settings import AISettings
from hbs_ads.core.errors import AppError
from hbs_ads.features.market_research.models import CreativeAnalysisResult
from hbs_ads.features.market_research.taxonomy import ANALYSIS_SCHEMA_VERSION
from hbs_ads.features.market_research.validators import validate_analysis_payload

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a mobile game ad creative analyst for market research.

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
- Controlled vocabulary fields must use only the allowed enum values."""

USER_PROMPT_TEMPLATE = """Analyze this mobile game ad video for creative market research.

Return JSON matching the required schema exactly.
schema_version must be "{schema_version}".

Required top-level keys: schema_version, asset_ref, observable, taxonomy_tags, interpretation, evidence, quality

observable required fields: duration_seconds, aspect_ratio, scene_count_estimate, contains_gameplay,
gameplay_visibility (enum: none/partial/full/unknown), creator_presence (enum: none/voice_only/hands_only/facecam/full_body/unknown),
character_presence, facecam_presence, device_frame_presence, text_overlay_present, text_overlay_summary,
voiceover_type, audio_style, cta_present, cta_text, cta_start_seconds, cta_end_seconds,
offer_present, offer_summary, visual_notes

taxonomy_tags required fields: hook_type (enum: direct_benefit/surprise_reveal/fail_then_win/social_proof/drama_conflict/challenge/curiosity_gap/transformation/before_after/claim_statistic/unknown),
format_type (enum: raw_gameplay/gameplay_plus_overlay/ugc_selfie/skit/meme_edit/fake_playable/static_to_motion/ai_avatar_voiceover/compilation/testimonial/unknown),
core_angle (enum: progression_reward/skill_mastery/relaxation/chaos_fail/collection_completion/story_drama/social_status/speed_efficiency/customization/survival_tension/unknown),
emotion_target, visual_device, proof_type,
cta_style (enum: direct_download/play_now/store_prompt/reward_claim/limited_offer/wishlist/unknown),
audience_hint, funnel_stage_guess (enum: prospecting/retargeting/reengagement/unknown)

interpretation required fields: hypothesized_strategy, why_it_might_work, likely_target_player, competitive_positioning_guess, novelty_assessment

evidence: array of objects with type, start_seconds, end_seconds, note

quality required fields: analysis_confidence, needs_human_review, failure_modes

Focus especially on these analysis dimensions: {analysis_focus}
Use controlled vocabularies exactly where specified.
Mark low confidence explicitly.
asset_ref: "{asset_ref}"
"""


_RETRYABLE_STATUS_CODES = {429, 503}
_MAX_RETRIES = 4
_RETRY_BASE_DELAY = 2.0  # seconds


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_with_retry(client: Any, model: str, contents: Any, timeout: int) -> Any:
    """Call generate_content with exponential backoff on 429/503 errors."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                request_options={"timeout": timeout},
            )
        except Exception as exc:
            status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            # google-genai may embed status in message; also check string
            is_retryable = status in _RETRYABLE_STATUS_CODES or any(
                str(s) in str(exc) for s in _RETRYABLE_STATUS_CODES
            )
            if not is_retryable or attempt == _MAX_RETRIES:
                raise
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Gemini rate limit hit (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, _MAX_RETRIES, delay, exc,
            )
            time.sleep(delay)
    raise RuntimeError("unreachable")


@dataclass(slots=True)
class GeminiMarketResearchAnalyzer:
    settings: AISettings

    def analyze_asset(
        self,
        asset_path: Path,
        run_id: str,
        asset_id: str,
        variant_cluster_id: str = "",
        analysis_focus: list[str] | None = None,
    ) -> CreativeAnalysisResult:
        focus = analysis_focus or ["hook_type", "format_type", "core_angle", "cta_style"]

        fixture = self._load_fixture(asset_path)
        if fixture is not None:
            errors = validate_analysis_payload(fixture)
            if errors:
                return self._build_failed_result(run_id, asset_id, variant_cluster_id, errors)
            return self._build_result(fixture, run_id, asset_id, variant_cluster_id)

        if self.settings.provider != "gemini":
            raise AppError(f"unsupported AI provider for market research analysis: {self.settings.provider}")

        api_key = os.environ.get(self.settings.gemini_api_key_env, "").strip()
        if not api_key:
            raise AppError(
                f"market research analysis requires {self.settings.gemini_api_key_env} env var"
            )

        try:
            from google import genai
        except ImportError as exc:
            raise AppError("market research analysis requires google-genai to be installed") from exc

        client = genai.Client(api_key=api_key)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            schema_version=ANALYSIS_SCHEMA_VERSION,
            asset_ref=asset_id,
            analysis_focus=", ".join(focus),
        )
        contents = [SYSTEM_PROMPT, user_prompt]

        if asset_path.exists():
            uploaded = client.files.upload(file=str(asset_path), config={"mime_type": "video/mp4"})
            try:
                for _ in range(30):
                    uploaded = client.files.get(name=uploaded.name)
                    if str(uploaded.state) == "FileState.ACTIVE":
                        break
                    time.sleep(3)
                else:
                    raise AppError(f"Gemini file never became ACTIVE: {asset_path.name}")
                contents = [uploaded] + contents
            except Exception:
                try:
                    client.files.delete(name=uploaded.name)
                except Exception:
                    pass
                raise

        try:
            response = _generate_with_retry(
                client, self.settings.clip_analysis_model, contents, timeout=90
            )
            raw_payload = self._parse_json(response.text)
            errors = validate_analysis_payload(raw_payload)
            if errors:
                repaired = self._attempt_repair(client, response.text, errors, user_prompt)
                if repaired is not None:
                    raw_payload = repaired
                else:
                    return self._build_failed_result(run_id, asset_id, variant_cluster_id, errors)
            return self._build_result(raw_payload, run_id, asset_id, variant_cluster_id)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(f"Gemini market research analysis failed for {asset_path.name}: {exc}") from exc
        finally:
            if asset_path.exists() and "uploaded" in dir():
                try:
                    client.files.delete(name=uploaded.name)  # type: ignore[possibly-undefined]
                except Exception:
                    pass

    def _attempt_repair(
        self,
        client: Any,
        original_text: str,
        errors: list[str],
        user_prompt: str,
    ) -> dict[str, Any] | None:
        repair_prompt = (
            f"The previous JSON response had validation errors:\n{chr(10).join(errors)}\n\n"
            f"Original response:\n{original_text}\n\n"
            "Return a corrected JSON object that fixes all listed errors. "
            "Return ONLY valid JSON with no markdown or commentary."
        )
        try:
            response = _generate_with_retry(
                client, self.settings.clip_analysis_model,
                [SYSTEM_PROMPT, user_prompt, repair_prompt], timeout=60,
            )
            repaired = self._parse_json(response.text)
            repair_errors = validate_analysis_payload(repaired)
            if not repair_errors:
                return repaired
            logger.warning("Repair attempt still invalid after retry; errors: %s", repair_errors)
        except Exception as exc:
            logger.warning("Repair attempt failed with exception: %s", exc)
        return None

    def _load_fixture(self, asset_path: Path) -> dict[str, Any] | None:
        for suffix in (".market-analysis.json", ".mr-analysis.json"):
            candidate = asset_path.with_name(f"{asset_path.name}{suffix}")
            if candidate.exists():
                return self._parse_json(candidate.read_text(encoding="utf-8"))
        return None

    def _parse_json(self, raw: str | None) -> dict[str, Any]:
        if not raw or not raw.strip():
            raise AppError("market research analysis returned an empty response")
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AppError(f"market research analysis response is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise AppError("market research analysis response must be a JSON object")
        return payload

    def _build_result(
        self,
        payload: dict[str, Any],
        run_id: str,
        asset_id: str,
        variant_cluster_id: str,
    ) -> CreativeAnalysisResult:
        return CreativeAnalysisResult(
            analysis_id=f"analysis_{asset_id}",
            run_id=run_id,
            asset_id=asset_id,
            variant_cluster_id=variant_cluster_id,
            model_provider="gemini",
            model_name=self.settings.clip_analysis_model,
            schema_version=payload.get("schema_version", ANALYSIS_SCHEMA_VERSION),
            observable=payload.get("observable", {}),
            taxonomy_tags=payload.get("taxonomy_tags", {}),
            interpretation=payload.get("interpretation", {}),
            evidence=payload.get("evidence", []),
            quality=payload.get("quality", {}),
            analysis_status="ok",
            created_at=_now_iso(),
        )

    def _build_failed_result(
        self,
        run_id: str,
        asset_id: str,
        variant_cluster_id: str,
        errors: list[str],
    ) -> CreativeAnalysisResult:
        return CreativeAnalysisResult(
            analysis_id=f"analysis_{asset_id}",
            run_id=run_id,
            asset_id=asset_id,
            variant_cluster_id=variant_cluster_id,
            model_provider="gemini",
            model_name=self.settings.clip_analysis_model,
            schema_version=ANALYSIS_SCHEMA_VERSION,
            quality={"failure_modes": errors, "needs_human_review": True, "analysis_confidence": 0.0},
            analysis_status="failed_validation",
            created_at=_now_iso(),
        )
