from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import re


@dataclass(frozen=True, slots=True)
class CommandSpec:
    argv: tuple[str, ...]
    shell: str | None = None

    @property
    def display(self) -> str:
        if self.shell:
            return f"{self.shell} -c " + " ".join(self.argv)
        return " ".join(self.argv)


@dataclass(frozen=True, slots=True)
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    started_at: datetime
    timed_out: bool = False

    def output_for(self, stderr_mode: str = "combined") -> str:
        if stderr_mode == "hidden":
            return self.stdout
        if stderr_mode == "separate":
            if self.stderr:
                return f"{self.stdout.rstrip()}\n\n--- stderr ---\n{self.stderr.rstrip()}" if self.stdout else self.stderr
            return self.stdout
        if self.stdout and self.stderr:
            return f"{self.stdout.rstrip()}\n{self.stderr.rstrip()}"
        return self.stdout or self.stderr

    @property
    def combined_output(self) -> str:
        return self.output_for("combined")

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def as_dict(self, sequence: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": round(self.duration_ms, 3),
            "started_at": self.started_at.isoformat(),
            "timed_out": self.timed_out,
            "ok": self.ok,
        }
        if sequence is not None:
            payload["sequence"] = sequence
        return payload

    def alert_triggered(self, pattern: str | None, stderr_mode: str = "combined") -> bool:
        return pattern is not None and re.search(pattern, self.output_for(stderr_mode)) is not None


@dataclass(frozen=True, slots=True)
class Frame:
    result: CommandResult
    lines: tuple[str, ...]
    sequence: int
    captured_at: datetime = field(default_factory=datetime.now)
