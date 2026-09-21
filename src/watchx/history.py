from __future__ import annotations

from collections import deque

from watchx.models import Frame


class FrameHistory:
    """Bounded in-memory frame history."""

    def __init__(self, maxlen: int = 100) -> None:
        if maxlen < 1:
            raise ValueError("history size must be at least 1")
        self._frames: deque[Frame] = deque(maxlen=maxlen)

    def append(self, frame: Frame) -> None:
        self._frames.append(frame)

    def snapshot(self) -> tuple[Frame, ...]:
        return tuple(self._frames)

    def __len__(self) -> int:
        return len(self._frames)
