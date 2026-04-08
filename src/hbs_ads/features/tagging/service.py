from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from hbs_ads.core.outputs import CommandResult
from hbs_ads.infra.db.sqlite import SQLiteDatabase
from hbs_ads.infra.ai.gemini import ClipAnalyzer


@dataclass(slots=True)
class AutoTagRequest:
    workspace_root: Path


@dataclass(slots=True)
class TagAIRequest:
    workspace_root: Path
    only_low_confidence: bool = False


@dataclass(slots=True)
class ApproveTagsRequest:
    workspace_root: Path
    approve_all: bool = False


@dataclass(slots=True)
class PendingTagsRequest:
    workspace_root: Path


class TaggingService:
    def __init__(self, database: SQLiteDatabase, analyzer: ClipAnalyzer | None = None) -> None:
        self.database = database
        self.analyzer = analyzer

    def auto(self, request: AutoTagRequest) -> CommandResult:
        clips = self.database.list_clips(pending_only=True)
        updated = 0
        for clip in clips:
            if clip.tags:
                continue
            tags = [part for part in re.split(r"[^a-zA-Z0-9]+", Path(clip.path).stem.lower()) if part]
            self.database.set_tags(clip.path, tags or ["untagged"], status="tagged")
            updated += 1
        return CommandResult(
            status="ok",
            message=f"tag auto completed for {updated} clips",
            data={"updated": updated},
        )

    def ai(self, request: TagAIRequest) -> CommandResult:
        clips = self.database.list_clips(pending_only=True)
        if request.only_low_confidence:
            clips = [clip for clip in clips if clip.confidence == "low"]
        if self.analyzer is None:
            raise RuntimeError("tag ai requires a configured clip analyzer")

        updated = 0
        analyses: list[dict[str, object]] = []
        for clip in clips:
            if clip.gemini_tagged:
                continue
            analysis = self.analyzer.analyze_clip(Path(clip.path))
            tags = self._merge_tags(clip.tags or ["untagged"], analysis)
            self.database.update_clip_analysis(
                path=clip.path,
                tags=tags,
                status="ai-tagged",
                approved=False,
                confidence=str(analysis.get("confidence", "low") or "low"),
                gemini_tagged=True,
                analysis=analysis,
            )
            updated += 1
            analyses.append(
                {
                    "path": clip.path,
                    "confidence": analysis.get("confidence", "low"),
                    "cta_present": analysis.get("cta_present", False),
                    "cta_start_seconds": analysis.get("cta_start_seconds"),
                    "cta_end_seconds": analysis.get("cta_end_seconds"),
                }
            )
        return CommandResult(
            status="ok",
            message=f"tag ai completed for {updated} clips",
            data={
                "updated": updated,
                "only_low_confidence": request.only_low_confidence,
                "analyses": analyses,
            },
        )

    def approve(self, request: ApproveTagsRequest) -> CommandResult:
        approved = self.database.approve_all() if request.approve_all else 0
        return CommandResult(
            status="ok",
            message=f"tag approve completed for {approved} clips",
            data={"approved": approved, "all": request.approve_all},
        )

    def pending(self, request: PendingTagsRequest) -> CommandResult:
        pending = self.database.list_clips(pending_only=True)
        return CommandResult(
            status="ok",
            message=f"tag pending found {len(pending)} clips",
            data={"pending": [clip.path for clip in pending]},
        )

    def _merge_tags(self, existing: list[str], analysis: dict[str, object]) -> list[str]:
        merged = list(existing)
        for candidate in (
            str(analysis.get("concept", "") or ""),
            str(analysis.get("vibe", "") or ""),
            str(analysis.get("style", "") or ""),
        ):
            if candidate and candidate not in merged:
                merged.append(candidate)
        if "ai-reviewed" not in merged:
            merged.append("ai-reviewed")
        if analysis.get("cta_present") and "cta" not in merged:
            merged.append("cta")
        return merged
