from datetime import datetime

from watchx.models import CommandResult, Frame
from watchx.session import read_frames, write_frames


def test_session_round_trip(tmp_path) -> None:
    result = CommandResult("out\n", "err\n", 0, 12.5, datetime.now())
    frame = Frame(result, ("out", "err"), 1)
    path = tmp_path / "session.jsonl"

    write_frames(path, (frame,))
    loaded = read_frames(path)

    assert len(loaded) == 1
    assert loaded[0].sequence == 1
    assert loaded[0].result.stdout == "out\n"
    assert loaded[0].lines == ("out", "err")
