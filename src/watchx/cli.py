from __future__ import annotations

import argparse
import re
import sys
from dataclasses import replace
from pathlib import Path

from watchx import __version__
from watchx.config import WatchConfig, load_config, write_default_config
from watchx.models import CommandSpec, Trigger

_DURATION_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)(ms|s|m|h)?$", re.IGNORECASE)


def parse_duration(value: str) -> float:
    """Parse 500ms, 2s, 1.5m, or a bare number in seconds."""
    match = _DURATION_RE.fullmatch(value.strip())
    if not match:
        raise argparse.ArgumentTypeError("invalid duration; use 500ms, 2s, 1.5m, or 1h")
    amount = float(match.group(1))
    unit = (match.group(2) or "s").lower()
    seconds = amount * {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}[unit]
    if seconds <= 0:
        raise argparse.ArgumentTypeError("duration must be greater than zero")
    return seconds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="watchx",
        description="A modern interactive watch utility for terminal commands.",
    )
    parser.add_argument(
        "-i", "--interval", type=parse_duration, help="refresh interval (default: 2s)"
    )
    parser.add_argument("--diff", action="store_true", help="highlight output changes")
    parser.add_argument("--no-diff", action="store_true", help="disable diff highlighting")
    parser.add_argument("--mouse", dest="mouse", action="store_true", default=None)
    parser.add_argument("--no-mouse", dest="mouse", action="store_false", default=None)
    parser.add_argument("--inline", action="store_true", help="use compact inline rendering")
    parser.add_argument(
        "--plain", action="store_true", help="use compact live output without TUI chrome"
    )
    parser.add_argument(
        "--shell",
        choices=("powershell", "pwsh", "cmd", "bash"),
        help="execute the command through a shell instead of direct process execution",
    )
    parser.add_argument(
        "--stderr",
        choices=("combined", "separate", "hidden"),
        help="stderr handling (default: combined)",
    )
    parser.add_argument("--theme", help="TUI theme name")
    parser.add_argument("--history-size", type=int, help="number of frames kept in memory")
    parser.add_argument("--history-line-cap", type=int, help="maximum lines retained per frame")
    parser.add_argument(
        "--exit-on-error", action="store_true", help="stop watching after a command failure"
    )
    parser.add_argument("--timeout", type=parse_duration, help="per-invocation command timeout")
    parser.add_argument(
        "--max-output", type=int, help="maximum captured output bytes per invocation"
    )
    parser.add_argument(
        "--retry", type=int, default=None, help="retry failed commands this many times"
    )
    parser.add_argument("--json", action="store_true", help="emit one JSON object per refresh")
    parser.add_argument(
        "--timestamp", action="store_true", help="include timestamps in compact output"
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="set command environment variable",
    )
    parser.add_argument("--once", action="store_true", help="run one refresh and exit")
    parser.add_argument(
        "--fail-if", metavar="REGEX", help="fail when output matches this regular expression"
    )
    parser.add_argument(
        "--trigger",
        action="append",
        default=[],
        metavar="REGEX[:ACTION]",
        help="alert on output; ACTION is sound, notify, or exit_code",
    )
    parser.add_argument(
        "--status-port", type=int, default=None, help="serve localhost health JSON on this port"
    )
    parser.add_argument("--status-token", help="bearer token required for status endpoints")
    parser.add_argument("--export-session", type=str, help="save captured frames as JSONL on exit")
    parser.add_argument("--store", type=str, help="append invocations to a SQLite database")
    parser.add_argument("--replay", type=str, help="replay a saved JSONL session and exit")
    parser.add_argument(
        "--replay-delay", type=parse_duration, default=0.0, help="delay between replayed frames"
    )
    parser.add_argument(
        "--init-config", action="store_true", help="create a default config file and exit"
    )
    parser.add_argument("--version", action="version", version=f"watchx {__version__}")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command and its arguments")
    return parser


def normalize_command(command: list[str]) -> tuple[str, ...]:
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("no command supplied")
    return tuple(command)


def resolve_config(args: argparse.Namespace) -> WatchConfig:
    config = load_config()
    config = replace(
        config,
        interval_seconds=args.interval if args.interval is not None else config.interval_seconds,
        diff=False if args.no_diff else (True if args.diff else config.diff),
        mouse=args.mouse if args.mouse is not None else config.mouse,
        theme=args.theme or config.theme,
        history_size=args.history_size if args.history_size is not None else config.history_size,
        history_line_cap=args.history_line_cap
        if args.history_line_cap is not None
        else config.history_line_cap,
        fullscreen=not args.inline and not args.plain,
        shell=args.shell if args.shell is not None else config.shell,
        stderr=args.stderr or config.stderr,
        exit_on_error=args.exit_on_error or config.exit_on_error,
        timeout_seconds=args.timeout if args.timeout is not None else config.timeout_seconds,
        max_output_bytes=args.max_output
        if args.max_output is not None
        else config.max_output_bytes,
        retries=args.retry if args.retry is not None else config.retries,
        timestamp=args.timestamp or config.timestamp,
        environment=tuple(parse_environment(args.env)) if args.env else config.environment,
        once=args.once,
        fail_if=args.fail_if if args.fail_if is not None else config.fail_if,
        status_port=args.status_port if args.status_port is not None else config.status_port,
        status_token=args.status_token if args.status_token is not None else config.status_token,
        export_session=Path(args.export_session)
        if args.export_session is not None
        else config.export_session,
        store_path=Path(args.store) if args.store is not None else config.store_path,
        triggers=parse_triggers(args.trigger) if args.trigger else config.triggers,
    )
    if config.history_size < 1:
        raise ValueError("history size must be at least 1")
    if config.history_line_cap < 1:
        raise ValueError("history line cap must be at least 1")
    if config.timeout_seconds is not None and config.timeout_seconds <= 0:
        raise ValueError("timeout must be greater than zero")
    if config.max_output_bytes < 1024:
        raise ValueError("max output must be at least 1024 bytes")
    if config.retries < 0:
        raise ValueError("retry count must not be negative")
    if not 0 <= config.status_port <= 65535:
        raise ValueError("status port must be between 0 and 65535")
    if config.status_token is not None and len(config.status_token) < 16:
        raise ValueError("status token must be at least 16 characters")
    if config.fail_if is not None:
        try:
            re.compile(config.fail_if)
        except re.error as exc:
            raise ValueError(f"invalid fail-if regular expression: {exc}") from exc
    for trigger in config.triggers:
        if trigger.action not in {"sound", "notify", "exit_code"}:
            raise ValueError("trigger action must be sound, notify, or exit_code")
        if trigger.pattern:
            try:
                re.compile(trigger.pattern)
            except re.error as exc:
                raise ValueError(f"invalid trigger regular expression: {exc}") from exc
    return config


def parse_environment(values: list[str]) -> list[tuple[str, str]]:
    result = []
    for value in values:
        key, separator, setting = value.partition("=")
        if not separator or not key:
            raise ValueError(f"invalid environment setting: {value!r}; use KEY=VALUE")
        result.append((key, setting))
    return result


def parse_triggers(values: list[str]) -> tuple[Trigger, ...]:
    result: list[Trigger] = []
    for value in values:
        pattern, separator, action = value.rpartition(":")
        if not separator:
            pattern, action = value, "exit_code"
        if not pattern:
            raise ValueError("trigger pattern must not be empty")
        result.append(Trigger(pattern, action))
    return tuple(result)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.init_config:
        path = write_default_config()
        print(f"Created {path}")
        return 0

    try:
        config = resolve_config(args)
        command = normalize_command(args.command) if not args.replay else ()
    except ValueError as exc:
        build_parser().error(str(exc))

    spec = CommandSpec(command, config.shell)

    if args.replay:
        import time

        from watchx.session import read_frames

        frames = read_frames(Path(args.replay))
        for index, frame in enumerate(frames):
            if index and args.replay_delay:
                time.sleep(args.replay_delay)
            print(frame.result.output_for(config.stderr))
        return 0 if frames and frames[-1].result.ok else 1

    if args.plain or args.inline or args.json or args.once:
        from watchx.inline import run_inline

        return run_inline(spec, config, plain=args.plain, json_output=args.json)

    try:
        from watchx.tui.app import WatchXApp
    except ImportError as exc:  # pragma: no cover - environment dependent
        print(
            "watchx requires its TUI dependencies. Install with: python -m pip install -e .",
            file=sys.stderr,
        )
        print(f"Import error: {exc}", file=sys.stderr)
        return 2

    app = WatchXApp(spec, config)
    return int(app.run(mouse=config.mouse) or 0)
