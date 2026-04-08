from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ExecutionResult:
    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    dry_run: bool = False
    cwd: str | None = None


@dataclass(slots=True)
class CommandRunner:
    default_timeout: float | None = None
    env: dict[str, str] | None = field(default=None)

    def run(
        self,
        args: list[str],
        cwd: Path | None = None,
        dry_run: bool = False,
        timeout: float | None = None,
    ) -> ExecutionResult:
        if dry_run:
            return ExecutionResult(
                args=args,
                returncode=0,
                stdout="",
                stderr="",
                duration_ms=0,
                dry_run=True,
                cwd=str(cwd) if cwd else None,
            )

        started = time.perf_counter()
        completed = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=timeout if timeout is not None else self.default_timeout,
            check=False,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ExecutionResult(
            args=args,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
            dry_run=False,
            cwd=str(cwd) if cwd else None,
        )
