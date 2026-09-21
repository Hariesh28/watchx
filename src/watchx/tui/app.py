from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Footer, Input, RichLog, Static
from textual.worker import Worker, get_current_worker

from watchx.config import WatchConfig
from watchx.diff import diff_lines
from watchx.history import FrameHistory
from watchx.models import CommandResult, CommandSpec, Frame
from watchx.runner import CommandCancelled, CommandRunner
from watchx.status import StatusServer
from watchx.session import write_frames


class WatchXApp(App[int]):
    """Interactive fullscreen watch application."""

    CSS_PATH = str(Path(__file__).with_name("watchx.tcss"))
    TITLE = "watchx"
    ENABLE_COMMAND_PALETTE = True

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("+", "faster", "Faster", show=False),
        Binding("=", "faster", "Faster", show=False),
        Binding("-", "slower", "Slower", show=False),
        Binding("0", "reset_interval", "Reset", show=False),
        Binding("d", "toggle_diff", "Diff"),
        Binding("/", "search", "Search"),
        Binding("escape", "close_search", "Close", show=False),
        Binding("h", "show_history", "History"),
        Binding("?", "help", "Help"),
    ]

    def __init__(self, spec: CommandSpec, config: WatchConfig) -> None:
        super().__init__()
        self.spec = spec
        self.config = config
        self.runner = CommandRunner(
            spec,
            timeout_seconds=config.timeout_seconds,
            max_output_bytes=config.max_output_bytes,
            environment=config.environment,
        )
        self.history = FrameHistory(config.history_size)
        self.previous_lines: tuple[str, ...] | None = None
        self.sequence = 0
        self.last_result: CommandResult | None = None
        self.paused = False
        self.running = False
        self.spinner_index = 0
        self.spinner_frames = ("◐", "◓", "◑", "◒")
        self.search_term = ""
        self.refresh_timer: Timer | None = None
        self.spinner_timer: Timer | None = None
        self.active_worker: Worker[CommandResult] | None = None
        self.status_server = StatusServer(config.status_port, self._status_snapshot) if config.status_port else None

    def compose(self) -> ComposeResult:
        yield Static(id="brand")
        with Vertical(id="chrome"):
            yield Static(id="command")
            with Horizontal(id="metrics"):
                yield Static(id="state")
                yield Static(id="stats")
                yield Static(id="clock")
            yield Input(placeholder="Search output…", id="search", classes="hidden")
            yield RichLog(id="output", wrap=False, highlight=False, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        if self.status_server:
            self.status_server.start()
            print(f"watchx status server: http://127.0.0.1:{self.status_server.port}/health", file=sys.stderr)
            print(f"watchx status token: {self.status_server.token}", file=sys.stderr)
        self._render_header()
        self.spinner_timer = self.set_interval(0.2, self._tick_spinner)
        self._reset_refresh_timer()
        self.refresh_command()

    def _status_snapshot(self) -> dict[str, object]:
        if self.last_result is None:
            return {"ok": False, "running": self.running, "sequence": self.sequence}
        payload = self.last_result.as_dict(self.sequence)
        payload["running"] = self.running
        payload["alert_triggered"] = self.last_result.alert_triggered(self.config.fail_if, self.config.stderr)
        payload["ok"] = not (not self.last_result.ok or payload["alert_triggered"])
        return payload

    def on_unmount(self) -> None:
        if self.config.export_session:
            write_frames(self.config.export_session, self.history.snapshot())
        if self.status_server:
            self.status_server.close()

    def _reset_refresh_timer(self) -> None:
        if self.refresh_timer:
            self.refresh_timer.stop()
        self.refresh_timer = self.set_interval(self.config.interval_seconds, self._scheduled_refresh)

    def _scheduled_refresh(self) -> None:
        if not self.paused:
            self.refresh_command()

    def _tick_spinner(self) -> None:
        if self.running:
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
            self._render_status()

    def _render_header(self) -> None:
        self.query_one("#brand", Static).update("watchx")
        self.query_one("#command", Static).update(self.spec.display)
        self._render_status()

    def _render_status(self) -> None:
        state = self.query_one("#state", Static)
        stats = self.query_one("#stats", Static)
        clock = self.query_one("#clock", Static)

        if self.running:
            state.update(f"{self.spinner_frames[self.spinner_index]} LIVE")
        elif self.paused:
            state.update("Ⅱ PAUSED")
        elif self.last_result is None:
            state.update("○ STARTING")
        elif self.last_result.ok:
            state.update("● READY")
        else:
            state.update(f"▲ EXIT {self.last_result.exit_code}")

        if self.last_result:
            stats.update(
                f"{self.config.interval_seconds:g}s  •  "
                f"{self.last_result.duration_ms:.0f}ms  •  "
                f"#{self.sequence}"
            )
        else:
            stats.update(f"{self.config.interval_seconds:g}s")
        clock.update(datetime.now().strftime("%H:%M:%S"))

    def refresh_command(self) -> None:
        """Start one refresh unless another refresh is still executing."""
        if self.running or self.paused:
            return
        self.running = True
        self._render_status()
        self.active_worker = self.run_worker(self._execute_once, thread=True, exclusive=False, exit_on_error=False)

    def _execute_once(self) -> CommandResult:
        """Execute exactly one command invocation outside the UI event loop."""
        worker = get_current_worker()
        try:
            for attempt in range(self.config.retries + 1):
                result = self.runner.run(should_cancel=lambda: worker.is_cancelled)
                if result.ok or attempt == self.config.retries:
                    return result
            raise RuntimeError("retry loop ended without a command result")
        except CommandCancelled:
            raise

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self.active_worker:
            return
        if event.worker.state.name == "SUCCESS":
            self.running = False
            result = event.worker.result
            if result is not None:
                self._apply_result(result)
        elif event.worker.state.name in {"ERROR", "CANCELLED"}:
            self.running = False
            self._render_status()

    def _apply_result(self, result: CommandResult) -> None:
        self.sequence += 1
        self.last_result = result
        lines = tuple(result.output_for(self.config.stderr).splitlines())
        frame = Frame(result=result, lines=lines, sequence=self.sequence)
        self.history.append(frame)
        self._render_output(lines)
        self.previous_lines = lines
        self._render_status()

        failed = not result.ok or result.alert_triggered(self.config.fail_if, self.config.stderr)
        if self.config.once or (self.config.exit_on_error and failed):
            self.exit(result.exit_code if not result.ok else (1 if failed else 0))

    def _render_output(self, lines: tuple[str, ...]) -> None:
        output = self.query_one("#output", RichLog)
        output.clear()
        render_lines = lines
        if self.search_term:
            render_lines = tuple(line for line in lines if self.search_term in line.casefold())

        if self.config.diff:
            diff = diff_lines(self.previous_lines, lines)
            for item in diff.lines:
                if self.search_term and self.search_term not in item.text.casefold():
                    continue
                if item.kind == "added":
                    output.write(Text(f"+ {item.text}", style="bold green"))
                elif item.kind == "removed":
                    output.write(Text(f"- {item.text}", style="dim red"))
                elif item.kind == "changed":
                    output.write(Text(item.text, style="bold yellow"))
                else:
                    output.write(item.text)
            changed_label = f"↑ {diff.changed_count} changed"
        else:
            for line in render_lines:
                output.write(Text.from_ansi(line))
            changed_label = "diff off"

        if not render_lines:
            output.write(Text("<no matching output>" if self.search_term else "<no output>", style="dim"))

        if self.last_result:
            self.query_one("#stats", Static).update(
                f"{self.config.interval_seconds:g}s  •  {self.last_result.duration_ms:.0f}ms  •  "
                f"#{self.sequence}  •  {changed_label}"
            )

    def action_quit(self) -> None:
        if self.active_worker and self.active_worker.state.name == "RUNNING":
            self.active_worker.cancel()
        self.exit(self.last_result.exit_code if self.last_result and not self.last_result.ok else 0)

    def action_refresh(self) -> None:
        if not self.running:
            self.refresh_command()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._render_status()
        if not self.paused:
            self.refresh_command()

    def action_faster(self) -> None:
        self._set_interval(max(0.1, self.config.interval_seconds / 2))

    def action_slower(self) -> None:
        self._set_interval(min(3600.0, self.config.interval_seconds * 2))

    def action_reset_interval(self) -> None:
        self._set_interval(2.0)

    def _set_interval(self, value: float) -> None:
        self.config = replace(self.config, interval_seconds=value)
        self._reset_refresh_timer()
        self._render_status()

    def action_toggle_diff(self) -> None:
        self.config = replace(self.config, diff=not self.config.diff)
        if self.last_result:
            self._render_output(tuple(self.last_result.output_for(self.config.stderr).splitlines()))

    def action_search(self) -> None:
        search = self.query_one("#search", Input)
        search.remove_class("hidden")
        search.focus()

    def action_close_search(self) -> None:
        search = self.query_one("#search", Input)
        search.value = ""
        self.search_term = ""
        search.add_class("hidden")
        if self.last_result:
            self._render_output(tuple(self.last_result.output_for(self.config.stderr).splitlines()))
        self.query_one("#output", RichLog).focus()

    def on_input_changed(self, message: Input.Changed) -> None:
        if message.input.id != "search":
            return
        self.search_term = message.value.casefold()
        if self.last_result:
            self._render_output(tuple(self.last_result.output_for(self.config.stderr).splitlines()))

    def action_show_history(self) -> None:
        from watchx.tui.screens import HistoryScreen

        self.push_screen(HistoryScreen(self.history.snapshot()))

    def action_help(self) -> None:
        from watchx.tui.screens import HelpScreen

        self.push_screen(HelpScreen())
