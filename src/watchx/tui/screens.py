from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Label, RichLog, Static

from watchx.diff import diff_lines, intraline_spans
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
        table.cursor_type = "row"
        table.add_columns("Frame", "Time", "Exit", "Runtime", "Lines")
        for frame in reversed(self.frames):
            table.add_row(
                f"#{frame.sequence}",
                frame.captured_at.strftime("%H:%M:%S"),
                str(frame.result.exit_code),
                f"{frame.result.duration_ms:.0f}ms",
                str(len(frame.lines)),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        index = event.cursor_row
        frames = tuple(reversed(self.frames))
        previous = frames[index + 1] if index + 1 < len(frames) else None
        self.app.push_screen(FrameDetailScreen(frames[index], previous))


class FrameDetailScreen(ModalScreen[None]):
    BINDINGS = [("escape", "dismiss", "Close"), ("q", "dismiss", "Close")]

    def __init__(self, frame: Frame, previous: Frame | None) -> None:
        super().__init__()
        self.frame = frame
        self.previous = previous

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-wide"):
            yield Static(f"FRAME #{self.frame.sequence}", id="dialog-title")
            yield RichLog(id="frame-detail", wrap=False, highlight=False, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#frame-detail", RichLog)
        current = self.frame.lines
        result = diff_lines(self.previous.lines if self.previous else None, current)
        for item in result.lines:
            if item.kind == "changed":
                text = Text()
                for chunk, changed in intraline_spans(item.previous_text or "", item.text):
                    text.append(chunk, style="reverse bold yellow" if changed else "yellow")
                log.write(text)
            elif item.kind == "added":
                log.write(Text(f"+ {item.text}", style="bold green"))
            elif item.kind == "removed":
                log.write(Text(f"- {item.text}", style="dim red"))
            else:
                log.write(item.text)
