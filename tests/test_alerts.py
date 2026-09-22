from datetime import datetime

from watchx.alerts import triggered
from watchx.models import CommandResult, Trigger


def test_exit_code_trigger_matches_result() -> None:
    result = CommandResult("", "", 2, 1.0, datetime.now())

    assert triggered(result, (Trigger(on_exit_code=2),), "combined")


def test_non_exit_trigger_does_not_mark_command_failed() -> None:
    result = CommandResult("ERROR", "", 0, 1.0, datetime.now())

    assert not triggered(result, (Trigger("ERROR", "notify"),), "combined")
