from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from hbs_ads.app.settings import AISettings
from hbs_ads.core.errors import AppError


class ClipAnalyzer(Protocol):
    def analyze_clip(self, clip_path: Path) -> dict[str, object]: ...


GEMINI_CLIP_ANALYSIS_PROMPT = """You are a mobile game ad video analyst.
Watch this clip and return ONLY valid JSON with no markdown or explanation.

Required fields:
{
  "concept": "<one of: merge, idle, upgrade, puzzle, asmr_wood, asmr, relaxing, fail, story, character, combat, build, other>",
  "vibe": "<one of: asmr_calm, lofi_chill, satisfying, upbeat, tension, fail_sad, funny, no_audio, other>",
  "style": "<one of: 2d, 3d, real_life, pixel, mixed, other>",
  "has_sfx": true,
  "text_on_screen": "<visible text or empty string>",
  "notes": "<one sentence description>",
  "confidence": "<one of: low, medium, high>",
  "cta_present": true,
  "cta_text": "<cta text or empty string>",
  "cta_start_seconds": 0.0,
  "cta_end_seconds": 0.0,
  "total_duration_seconds": 0.0
}

Rules:
- If no CTA is present, set cta_present to false, cta_text to "", and CTA seconds to null.
- CTA timing should describe when the clear call to action first appears and when it ends.
- Use null for any timing you cannot determine confidently."""


@dataclass(slots=True)
class GeminiClipAnalyzer:
    settings: AISettings

    def analyze_clip(self, clip_path: Path) -> dict[str, object]:
        fixture = self._load_fixture(clip_path)
        if fixture is not None:
            return self._normalize_analysis(fixture)

        if self.settings.provider != "gemini":
            raise AppError(f"unsupported AI provider for clip analysis: {self.settings.provider}")

        api_key = os.environ.get(self.settings.gemini_api_key_env, "").strip()
        if not api_key:
            raise AppError(
                f"tag ai requires {self.settings.gemini_api_key_env} or a clip-sidecar analysis fixture"
            )

        try:
            from google import genai
        except ImportError as exc:
            raise AppError("tag ai requires google-genai to be installed") from exc

        client = genai.Client(api_key=api_key)
        uploaded = client.files.upload(file=str(clip_path), config={"mime_type": "video/mp4"})
        try:
            for _attempt in range(30):
                uploaded = client.files.get(name=uploaded.name)
                if str(uploaded.state) == "FileState.ACTIVE":
                    break
                time.sleep(3)
            else:
                raise AppError(f"Gemini file never became ACTIVE: {clip_path.name}")

            response = None
            for retry in range(3):
                try:
                    response = client.models.generate_content(
                        model=self.settings.clip_analysis_model,
                        contents=[uploaded, GEMINI_CLIP_ANALYSIS_PROMPT],
                        request_options={"timeout": 60},
                    )
                    break
                except Exception as retry_exc:
                    if "429" in str(retry_exc) or "quota" in str(retry_exc).lower():
                        if retry < 2:
                            time.sleep(2 ** (retry + 1))
                            continue
                    raise
            if response is None:
                raise AppError(f"Gemini quota exhausted after retries: {clip_path.name}")
            return self._normalize_analysis(self._parse_json(response.text))
        except Exception as exc:
            if isinstance(exc, AppError):
                raise
            raise AppError(f"tag ai Gemini analysis failed for {clip_path.name}: {exc}") from exc
        finally:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass

    def _load_fixture(self, clip_path: Path) -> dict[str, object] | None:
        for suffix in (".analysis.json", ".gemini.json"):
            candidate = clip_path.with_name(f"{clip_path.name}{suffix}")
            if candidate.exists():
                return self._parse_json(candidate.read_text(encoding="utf-8"))
        return None

    def _parse_json(self, raw: str) -> dict[str, object]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        payload = json.loads(cleaned)
        if not isinstance(payload, dict):
            raise AppError("clip analysis response must be a JSON object")
        return payload

    def _normalize_analysis(self, payload: dict[str, object]) -> dict[str, object]:
        normalized = dict(payload)
        normalized["concept"] = str(payload.get("concept", "other") or "other")
        normalized["vibe"] = str(payload.get("vibe", "other") or "other")
        normalized["style"] = str(payload.get("style", "other") or "other")
        normalized["has_sfx"] = bool(payload.get("has_sfx", False))
        normalized["text_on_screen"] = str(payload.get("text_on_screen", "") or "")
        normalized["notes"] = str(payload.get("notes", "") or "")
        normalized["confidence"] = str(payload.get("confidence", "low") or "low")
        normalized["cta_present"] = bool(payload.get("cta_present", False))
        normalized["cta_text"] = str(payload.get("cta_text", "") or "")
        normalized["cta_start_seconds"] = self._coerce_number(payload.get("cta_start_seconds"))
        normalized["cta_end_seconds"] = self._coerce_number(payload.get("cta_end_seconds"))
        normalized["total_duration_seconds"] = self._coerce_number(payload.get("total_duration_seconds"))
        return normalized

    def _coerce_number(self, value: object) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
