from __future__ import annotations

import time
from collections.abc import Callable

from watchx.models import CommandResult
from watchx.runner import CommandCancelled, CommandRunner


def run_with_retries(
    runner: CommandRunner,
    retries: int,
    should_cancel: Callable[[], bool] | None = None,
    backoff: Callable[[int], float] | None = None,
) -> CommandResult:
    """Run a command, retrying failed invocations with bounded backoff."""
    delay = backoff or (lambda attempt: min(1.0, 0.1 * (attempt + 1)))
    for attempt in range(retries + 1):
        result = runner.run(should_cancel=should_cancel)
        if result.ok or attempt == retries:
            return result
        if should_cancel and should_cancel():
            raise CommandCancelled
        time.sleep(delay(attempt))
    raise RuntimeError("unreachable retry state")
