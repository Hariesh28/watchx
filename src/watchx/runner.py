from __future__ import annotations

import locale
import os
import signal
import subprocess
import time
from collections.abc import Callable
from datetime import datetime

from watchx.models import CommandResult, CommandSpec


class CommandCancelled(Exception):
    """Raised when the active command is cancelled by watchx."""


class CommandRunner:
    """Cross-platform command runner with cancellation and sequential semantics."""

    def __init__(
        self,
        spec: CommandSpec,
        timeout_seconds: float | None = None,
        max_output_bytes: int = 2_000_000,
        environment: tuple[tuple[str, str], ...] = (),
    ) -> None:
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if max_output_bytes < 1:
            raise ValueError("max_output_bytes must be greater than zero")
        self.spec = spec
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.environment = environment

    def _prepare(self) -> tuple[list[str] | str, bool]:
        if not self.spec.shell:
            return list(self.spec.argv), False

        if self.spec.shell in {"powershell", "pwsh"}:
            executable = "powershell.exe" if self.spec.shell == "powershell" else "pwsh.exe"
            command_text = _quote_for_powershell(self.spec.argv)
            return [executable, "-NoProfile", "-NonInteractive", "-Command", command_text], False
        if self.spec.shell == "cmd":
            command_text = subprocess.list2cmdline(list(self.spec.argv))
            return ["cmd.exe", "/d", "/c", command_text], False
        if self.spec.shell == "bash":
            return ["bash", "-lc", " ".join(self.spec.argv)], False
        raise ValueError(f"unsupported shell: {self.spec.shell}")

    def run(self, should_cancel: Callable[[], bool] | None = None) -> CommandResult:
        started = datetime.now()
        start = time.perf_counter()
        argv, shell = self._prepare()
        creationflags = 0
        start_new_session = os.name != "nt"
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        process = subprocess.Popen(
            argv,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            creationflags=creationflags,
            start_new_session=start_new_session,
            env={**os.environ, **dict(self.environment)},
        )
        timed_out = False
        try:
            while True:
                if should_cancel and should_cancel():
                    self._terminate(process)
                    raise CommandCancelled
                try:
                    stdout, stderr = process.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    if (
                        self.timeout_seconds is not None
                        and (time.perf_counter() - start) >= self.timeout_seconds
                    ):
                        timed_out = True
                        self._terminate(process)
                        stdout, stderr = process.communicate()
                        break

        except CommandCancelled:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._terminate(process)
                process.wait(timeout=5)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        stdout = self._truncate(_decode_output(stdout))
        stderr = self._truncate(_decode_output(stderr))
        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=process.returncode if process.returncode is not None else 1,
            duration_ms=duration_ms,
            started_at=started,
            timed_out=timed_out,
        )

    def _truncate(self, text: str) -> str:
        raw = text.encode("utf-8", errors="replace")
        if len(raw) <= self.max_output_bytes:
            return text
        truncated = raw[: self.max_output_bytes].decode("utf-8", errors="ignore")
        return truncated + "\n… [output truncated by watchx]"

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
                process.wait(timeout=1.5)
                return
            except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                pass
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except ProcessLookupError:
                return
            try:
                process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)


def _quote_for_powershell(argv: tuple[str, ...]) -> str:
    result: list[str] = []
    for value in argv:
        if len(value) >= 2 and value[0] == value[-1] == "'":
            result.append(value)
            continue
        if any(char.isspace() for char in value) or any(char in value for char in "'`$|;&<>"):
            result.append("'" + value.replace("'", "''") + "'")
        else:
            result.append(value)
    return " ".join(result)


def _decode_output(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode(locale.getpreferredencoding(False), errors="replace")
