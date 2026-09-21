from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Label, Static

from watchx.models import Frame


class HelpScreen(ModalScreen[None]):
    BINDINGS = [("escape", "dismiss", "Close"), ("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("WATCHX KEYS", id="dialog-title")
            yield Label(
                "q  quit\n"
                "r  refresh now\n"
                "p  pause / resume\n"
                "+  faster\n"
                "-  slower\n"
                "0  reset interval\n"
                "d  toggle diff\n"
                "/  search\n"
                "h  history\n"
                "?  help\n"
                "Esc  close overlay"
            )
        yield Footer()


class HistoryScreen(ModalScreen[None]):
    BINDINGS = [("escape", "dismiss", "Close"), ("q", "dismiss", "Close")]

    def __init__(self, frames: tuple[Frame, ...]) -> None:
        super().__init__()
        self.frames = frames

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-wide"):
            yield Static("WATCH HISTORY", id="dialog-title")
            yield DataTable(id="history-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.add_columns("Frame", "Time", "Exit", "Runtime", "Lines")
        for frame in reversed(self.frames):
            table.add_row(
                f"#{frame.sequence}",
                frame.captured_at.strftime("%H:%M:%S"),
                str(frame.result.exit_code),
                f"{frame.result.duration_ms:.0f}ms",
                str(len(frame.lines)),
            )
