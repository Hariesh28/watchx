import sys
import time

from watchx.models import CommandSpec
from watchx.runner import CommandCancelled, CommandRunner


def test_direct_process_execution() -> None:
    spec = CommandSpec((sys.executable, "-c", "print('watchx')"))
    result = CommandRunner(spec).run()
    assert result.exit_code == 0
    assert result.stdout.strip() == "watchx"


def test_output_limit_adds_truncation_marker() -> None:
    spec = CommandSpec((sys.executable, "-c", "print('x' * 5000)"))
    result = CommandRunner(spec, max_output_bytes=1024).run()
    assert "output truncated by watchx" in result.stdout
    assert len(result.stdout.encode("utf-8")) < 1200


def test_runner_captures_stdout_and_stderr_separately() -> None:
    spec = CommandSpec(
        (
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        )
    )

    result = CommandRunner(spec).run()

    assert result.stdout.strip() == "out"
    assert result.stderr.strip() == "err"


def test_runner_marks_timed_out_commands() -> None:
    spec = CommandSpec((sys.executable, "-c", "import time; time.sleep(2)"))

    result = CommandRunner(spec, timeout_seconds=0.1).run()

    assert result.timed_out
    assert result.exit_code != 0


def test_runner_cancels_commands() -> None:
    spec = CommandSpec((sys.executable, "-c", "import time; time.sleep(2)"))
    checks = 0

    def should_cancel() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    started = time.perf_counter()
    try:
        CommandRunner(spec).run(should_cancel=should_cancel)
    except CommandCancelled:
        assert time.perf_counter() - started < 2
    else:
        raise AssertionError("cancellation was ignored")


def test_shell_command_text_preserves_intentional_syntax() -> None:
    runner = CommandRunner(
        CommandSpec(("Get-Date", "-Format", "'HH:mm:ss.fff'"), shell="powershell")
    )

    argv, use_shell = runner._prepare()

    assert not use_shell
    assert argv[-1] == "Get-Date -Format 'HH:mm:ss.fff'"
