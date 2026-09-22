from __future__ import annotations

import re
import sys
from collections.abc import Iterable

from watchx.models import CommandResult, Trigger


def triggered(result: CommandResult, triggers: Iterable[Trigger], stderr_mode: str) -> bool:
    text = result.output_for(stderr_mode)
    return any(
        trigger.action == "exit_code"
        and (
            (trigger.pattern and re.search(trigger.pattern, text) is not None)
            or (trigger.on_exit_code is not None and trigger.on_exit_code == result.exit_code)
        )
        for trigger in triggers
    )


def dispatch(result: CommandResult, triggers: Iterable[Trigger], stderr_mode: str) -> bool:
    text = result.output_for(stderr_mode)
    exit_requested = False
    for trigger in triggers:
        matched = bool(trigger.pattern and re.search(trigger.pattern, text))
        matched = matched or (
            trigger.on_exit_code is not None and trigger.on_exit_code == result.exit_code
        )
        if not matched:
            continue
        if trigger.action == "sound" and sys.platform == "win32":
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        elif trigger.action == "notify":
            print(f"watchx alert: {trigger.pattern or f'exit {result.exit_code}'}", file=sys.stderr)
        elif trigger.action == "exit_code":
            exit_requested = True
    return exit_requested
