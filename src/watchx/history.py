from __future__ import annotations

from collections import deque

from watchx.models import Frame


class FrameHistory:
    """Bounded in-memory frame history."""

    def __init__(self, maxlen: int = 100, line_cap: int | None = None) -> None:
        if maxlen < 1:
            raise ValueError("history size must be at least 1")
        if line_cap is not None and line_cap < 1:
            raise ValueError("history line cap must be at least 1")
        self._frames: deque[Frame] = deque(maxlen=maxlen)
        self._line_cap = line_cap

    def append(self, frame: Frame) -> None:
        if self._line_cap is not None and len(frame.lines) > self._line_cap:
            frame = Frame(
                frame.result,
                frame.lines[-self._line_cap :],
                frame.sequence,
                frame.captured_at,
            )
        self._frames.append(frame)

    def snapshot(self) -> tuple[Frame, ...]:
        return tuple(self._frames)

    def __len__(self) -> int:
        return len(self._frames)
