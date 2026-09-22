from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True, slots=True)
class DiffLine:
    text: str
    kind: str  # same | changed | added | removed
    previous_text: str | None = None


@dataclass(frozen=True, slots=True)
class DiffResult:
    lines: tuple[DiffLine, ...]
    changed_count: int


def diff_lines(previous: tuple[str, ...] | None, current: tuple[str, ...]) -> DiffResult:
    """Produce a stable line-level diff suitable for an interactive TUI."""
    if previous is None:
        return DiffResult(tuple(DiffLine(line, "same") for line in current), 0)

    matcher = SequenceMatcher(a=previous, b=current, autojunk=False)
    rendered: list[DiffLine] = []
    changed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rendered.extend(DiffLine(line, "same") for line in current[j1:j2])
        elif tag == "replace":
            old_lines = previous[i1:i2]
            new_lines = current[j1:j2]
            for offset, line in enumerate(new_lines):
                old_line = old_lines[offset] if offset < len(old_lines) else None
                rendered.append(DiffLine(line, "changed", old_line))
                changed += 1
            for line in old_lines[len(new_lines) :]:
                rendered.append(DiffLine(line, "removed"))
        elif tag == "delete":
            for line in previous[i1:i2]:
                rendered.append(DiffLine(line, "removed"))
                changed += 1
        elif tag == "insert":
            for line in current[j1:j2]:
                rendered.append(DiffLine(line, "added"))
                changed += 1

    return DiffResult(tuple(rendered), changed)


def intraline_spans(old: str, new: str) -> tuple[tuple[str, bool], ...]:
    """Return text runs marking the characters changed between two lines."""
    matcher = SequenceMatcher(a=old, b=new, autojunk=False)
    return tuple(
        (new[j1:j2], tag != "equal") for tag, _i1, _i2, j1, j2 in matcher.get_opcodes() if j1 != j2
    )
