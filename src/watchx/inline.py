from __future__ import annotations

import json
import sys
import time
from datetime import datetime

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from watchx.alerts import dispatch, triggered
from watchx.config import WatchConfig
from watchx.execution import run_with_retries
from watchx.models import CommandSpec, Frame
from watchx.runner import CommandRunner
from watchx.session import write_frames
from watchx.status import StatusServer
from watchx.store import RunStore


def _render(spec: CommandSpec, result, frame: int, config: WatchConfig) -> Panel:
    body = result.output_for(config.stderr).rstrip() or "<no output>"
    status = "OK" if result.ok else f"EXIT {result.exit_code}"
    footer = f"{status}  •  {result.duration_ms:.0f}ms"
    if config.timestamp:
        footer += f"  •  {datetime.now():%H:%M:%S}"
    footer += f"  • refresh #{frame}"
    text = Text(body)
    return Panel(text, title=f" WATCHX  {spec.display} ", subtitle=footer)


def _failed(result, config: WatchConfig) -> bool:
    return (
        not result.ok
        or result.alert_triggered(config.fail_if, config.stderr)
        or triggered(result, config.triggers, config.stderr)
    )


def run_inline(
    spec: CommandSpec,
    config: WatchConfig,
    plain: bool = False,
    json_output: bool = False,
) -> int:
    runner = CommandRunner(
        spec,
        timeout_seconds=config.timeout_seconds,
        max_output_bytes=config.max_output_bytes,
        environment=config.environment,
    )
    captured: list[Frame] = []
    latest: dict[str, object] = {"ok": False, "running": True, "sequence": 0}
    status = (
        StatusServer(config.status_port, lambda: dict(latest), config.status_token)
        if config.status_port
        else None
    )
    store = RunStore(config.store_path, spec.display) if config.store_path else None

    def record(command_result, sequence: int) -> bool:
        fail_if_triggered = command_result.alert_triggered(config.fail_if, config.stderr)
        trigger_exit = dispatch(command_result, config.triggers, config.stderr)
        captured.append(
            Frame(
                command_result,
                tuple(command_result.output_for(config.stderr).splitlines())[
                    -config.history_line_cap :
                ],
                sequence,
            )
        )
        if store:
            store.record(captured[-1])
        latest.update(command_result.as_dict(sequence))
        latest["alert_triggered"] = fail_if_triggered or trigger_exit
        latest["ok"] = not _failed(command_result, config)
        latest["running"] = False
        return fail_if_triggered or trigger_exit

    try:
        if status:
            status.start()
            print(f"watchx status server: http://127.0.0.1:{status.port}/health", file=sys.stderr)
            print(f"watchx status token: {status.token}", file=sys.stderr)
        first = run_with_retries(runner, config.retries)
        first_alert = record(first, 1)
        if json_output:
            payload = first.as_dict(1)
            payload["alert_triggered"] = first_alert
            payload["ok"] = not _failed(first, config)
            print(json.dumps(payload, ensure_ascii=False), flush=True)
            if config.once or (config.exit_on_error and _failed(first, config)):
                return first.exit_code if not first.ok else (1 if payload["alert_triggered"] else 0)
            frame = 1
            while True:
                time.sleep(config.interval_seconds)
                frame += 1
                result = run_with_retries(runner, config.retries)
                alert_triggered = record(result, frame)
                payload = result.as_dict(frame)
                payload["alert_triggered"] = alert_triggered
                payload["ok"] = not _failed(result, config)
                print(json.dumps(payload, ensure_ascii=False), flush=True)
                if config.exit_on_error and _failed(result, config):
                    return result.exit_code or 1
        if config.once:
            if plain:
                print(first.output_for(config.stderr).rstrip() or "<no output>")
            else:
                print(first.output_for(config.stderr).rstrip() or "<no output>")
            return first.exit_code if not first.ok else (1 if first_alert else 0)
        initial = (
            Text(first.output_for(config.stderr).rstrip() or "<no output>")
            if plain
            else _render(spec, first, 1, config)
        )
        with Live(initial, refresh_per_second=12, screen=False) as live:
            frame = 1
            while True:
                time.sleep(config.interval_seconds)
                frame += 1
                result = run_with_retries(runner, config.retries)
                record(result, frame)
                live.update(
                    Text(result.output_for(config.stderr).rstrip() or "<no output>")
                    if plain
                    else _render(spec, result, frame, config),
                    refresh=True,
                )
                if config.exit_on_error and _failed(result, config):
                    return result.exit_code or 1
    except KeyboardInterrupt:
        return 130
    finally:
        if config.export_session:
            write_frames(config.export_session, tuple(captured))
        if status:
            status.close()
        if store:
            store.close()


def run_plain(spec: CommandSpec, config: WatchConfig) -> int:
    """Minimal live renderer for logs/scripts; intentionally no box UI."""
    return run_inline(spec, config)
