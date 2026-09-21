from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from watchx.models import CommandResult, Frame


def frame_to_dict(frame: Frame) -> dict[str, Any]:
    payload = frame.result.as_dict(frame.sequence)
    payload["lines"] = list(frame.lines)
    payload["captured_at"] = frame.captured_at.isoformat()
    return payload


def write_frames(path: Path, frames: tuple[Frame, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            for frame in frames:
                handle.write(json.dumps(frame_to_dict(frame), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        assert temporary_path is not None
        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def read_frames(path: Path) -> tuple[Frame, ...]:
    frames: list[Frame] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                result = CommandResult(
                    stdout=str(data["stdout"]),
                    stderr=str(data["stderr"]),
                    exit_code=int(data["exit_code"]),
                    duration_ms=float(data["duration_ms"]),
                    started_at=datetime.fromisoformat(data["started_at"]),
                    timed_out=bool(data.get("timed_out", False)),
                )
                sequence = int(data["sequence"])
                lines = tuple(
                    str(item) for item in data.get("lines", result.combined_output.splitlines())
                )
                captured_at = datetime.fromisoformat(data.get("captured_at", data["started_at"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid session record at line {line_number}") from exc
            frames.append(Frame(result, lines, sequence, captured_at))
    return tuple(frames)
