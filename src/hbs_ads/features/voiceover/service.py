from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.exec.runner import CommandRunner


@dataclass(slots=True)
class GenerateVoiceoverRequest:
    workspace_root: Path
    script: str = ""
    dry_run: bool = False


class VoiceoverService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        command_runner: CommandRunner,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.command_runner = command_runner

    def generate(self, request: GenerateVoiceoverRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        script = request.script.strip() or f"Voiceover generated for {layout.root.name}"
        slug = self._slugify(script[:40]) or "voiceover"
        transcript_path = layout.voiceover_dir / f"{slug}.txt"
        audio_path = layout.voiceover_dir / f"{slug}.mp3"
        manifest_path = layout.voiceover_dir / f"{slug}.json"

        preview = self.command_runner.run(
            args=["printf", "%s", script],
            cwd=layout.root,
            dry_run=request.dry_run,
        )
        manifest = {
            "provider": self.settings.voiceover.provider,
            "script": script,
            "transcript_file": str(transcript_path),
            "audio_file": str(audio_path),
            "preview_command": preview.args,
            "preview_dry_run": preview.dry_run,
        }
        if not request.dry_run:
            transcript_path.write_text(script + "\n", encoding="utf-8")
            audio_path.write_bytes(f"FAKE_MP3 provider={self.settings.voiceover.provider}\n{script}\n".encode("utf-8"))
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return CommandResult(
            status="planned" if request.dry_run else "ok",
            message=f"voiceover generate {'planned' if request.dry_run else 'completed'}",
            data={
                "provider": self.settings.voiceover.provider,
                "transcript_file": str(transcript_path),
                "audio_file": str(audio_path),
                "manifest_file": str(manifest_path),
                "dry_run": request.dry_run,
            },
        )

    def _slugify(self, value: str) -> str:
        slug = "".join(character.lower() if character.isalnum() else "-" for character in value.strip())
        return "-".join(part for part in slug.split("-") if part)
