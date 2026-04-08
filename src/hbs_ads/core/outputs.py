from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CommandResult:
    status: str
    message: str
    output_mode: str = "text"
    data: dict[str, object] = field(default_factory=dict)
