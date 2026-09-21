from datetime import datetime

from watchx.models import CommandResult


def make_result(stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=0,
        duration_ms=1.0,
        started_at=datetime.now(),
    )


def test_output_for_supports_all_stderr_modes() -> None:
    result = make_result("out\n", "err\n")

    assert result.output_for("combined") == "out\nerr"
    assert result.output_for("separate") == "out\n\n--- stderr ---\nerr"
    assert result.output_for("hidden") == "out\n"


def test_output_for_handles_stderr_without_stdout() -> None:
    assert make_result(stderr="err\n").output_for("separate") == "err\n"


def test_combined_output_uses_combined_mode() -> None:
    assert make_result("out", "err").combined_output == "out\nerr"


def test_result_as_dict_is_json_ready() -> None:
    payload = make_result("out").as_dict(3)

    assert payload["sequence"] == 3
    assert payload["ok"] is True
    assert payload["started_at"].startswith("20")


def test_alert_triggered_matches_selected_output() -> None:
    result = make_result("healthy", "ERROR: failed")

    assert result.alert_triggered("ERROR")
    assert not result.alert_triggered("ERROR", "hidden")
