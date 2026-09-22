from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypedDict

from watchx.models import Trigger


@dataclass(frozen=True, slots=True)
class WatchConfig:
    interval_seconds: float = 2.0
    diff: bool = False
    mouse: bool = True
    theme: str = "watchx-dark"
    history_size: int = 100
    history_line_cap: int = 500
    fullscreen: bool = True
    shell: str | None = None
    stderr: str = "combined"
    exit_on_error: bool = False
    timeout_seconds: float | None = None
    max_output_bytes: int = 2_000_000
    retries: int = 0
    timestamp: bool = False
    environment: tuple[tuple[str, str], ...] = ()
    once: bool = False
    fail_if: str | None = None
    status_port: int = 0
    status_token: str | None = None
    export_session: Path | None = None
    store_path: Path | None = None
    triggers: tuple[Trigger, ...] = ()


class ConfigUpdates(TypedDict, total=False):
    interval_seconds: float
    diff: bool
    mouse: bool
    theme: str
    history_size: int
    history_line_cap: int
    fullscreen: bool
    shell: str | None
    stderr: str
    exit_on_error: bool
    timeout_seconds: float | None
    max_output_bytes: int
    retries: int
    timestamp: bool
    environment: tuple[tuple[str, str], ...]
    fail_if: str | None
    status_port: int
    status_token: str | None
    export_session: Path
    store_path: Path
    triggers: tuple[Trigger, ...]


def config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "watchx" / "config.toml"


def load_config(path: Path | None = None) -> WatchConfig:
    path = path or config_path()
    if not path.exists():
        return WatchConfig()

    with path.open("rb") as handle:
        data = tomllib.load(handle)

    watch = data.get("watchx", {})
    if not isinstance(watch, dict):
        return WatchConfig()

    raw_shell = watch.get("shell")
    shell = raw_shell or None
    updates: ConfigUpdates = {}
    if "interval_seconds" in watch:
        updates["interval_seconds"] = float(watch["interval_seconds"])
    if "diff" in watch:
        updates["diff"] = bool(watch["diff"])
    if "mouse" in watch:
        updates["mouse"] = bool(watch["mouse"])
    if "theme" in watch:
        updates["theme"] = str(watch["theme"])
    if "history_size" in watch:
        updates["history_size"] = int(watch["history_size"])
    if "history_line_cap" in watch:
        updates["history_line_cap"] = int(watch["history_line_cap"])
    if "fullscreen" in watch:
        updates["fullscreen"] = bool(watch["fullscreen"])
    if "shell" in watch:
        updates["shell"] = shell
    if "stderr" in watch:
        updates["stderr"] = str(watch["stderr"])
    if "exit_on_error" in watch:
        updates["exit_on_error"] = bool(watch["exit_on_error"])
    if "timeout_seconds" in watch:
        raw_timeout = watch["timeout_seconds"]
        updates["timeout_seconds"] = None if raw_timeout in (None, "", 0) else float(raw_timeout)
    if "max_output_bytes" in watch:
        updates["max_output_bytes"] = int(watch["max_output_bytes"])
    if "retries" in watch:
        updates["retries"] = int(watch["retries"])
    if "timestamp" in watch:
        updates["timestamp"] = bool(watch["timestamp"])
    if "fail_if" in watch:
        updates["fail_if"] = str(watch["fail_if"]) or None
    if "environment" in watch and isinstance(watch["environment"], dict):
        updates["environment"] = tuple(
            (str(key), str(value)) for key, value in watch["environment"].items()
        )
    if "status_port" in watch:
        updates["status_port"] = int(watch["status_port"])
    if "status_token" in watch:
        updates["status_token"] = str(watch["status_token"]) or None
    if "export_session" in watch and watch["export_session"]:
        updates["export_session"] = Path(str(watch["export_session"]))
    if "store_path" in watch and watch["store_path"]:
        updates["store_path"] = Path(str(watch["store_path"]))
    if "triggers" in watch and isinstance(watch["triggers"], list):
        updates["triggers"] = tuple(
            Trigger(
                pattern=str(item.get("pattern", "")),
                action=str(item.get("action", "exit_code")),
                on_exit_code=(
                    int(item["on_exit_code"]) if item.get("on_exit_code") is not None else None
                ),
            )
            for item in watch["triggers"]
            if isinstance(item, dict)
        )

    config = replace(WatchConfig(), **updates)
    if config.interval_seconds <= 0:
        raise ValueError("watchx config interval_seconds must be greater than zero")
    if config.history_size < 1:
        raise ValueError("watchx config history_size must be at least 1")
    if config.history_line_cap < 1:
        raise ValueError("watchx config history_line_cap must be at least 1")
    if config.timeout_seconds is not None and config.timeout_seconds <= 0:
        raise ValueError("watchx config timeout_seconds must be greater than zero")
    if config.max_output_bytes < 1024:
        raise ValueError("watchx config max_output_bytes must be at least 1024")
    if config.retries < 0:
        raise ValueError("watchx config retries must not be negative")
    if config.stderr not in {"combined", "separate", "hidden"}:
        raise ValueError("watchx config stderr must be combined, separate, or hidden")
    if not 0 <= config.status_port <= 65535:
        raise ValueError("watchx config status_port must be between 0 and 65535")
    if config.status_token is not None and len(config.status_token) < 16:
        raise ValueError("watchx config status_token must be at least 16 characters")
    if any(trigger.action not in {"sound", "notify", "exit_code"} for trigger in config.triggers):
        raise ValueError("watchx trigger action must be sound, notify, or exit_code")
    return config


def write_default_config(path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# watchx configuration
[watchx]
interval_seconds = 2.0
diff = false
mouse = true
theme = "watchx-dark"
history_size = 100
history_line_cap = 500
fullscreen = true
shell = ""
stderr = "combined"
exit_on_error = false
timeout_seconds = 0
max_output_bytes = 2000000
retries = 0
timestamp = false
fail_if = ""
status_port = 0
# Leave empty to generate a secure token at startup.
status_token = ""
store_path = ""

# Optional alert rules:
# [[watchx.triggers]]
# pattern = "ERROR"
# action = "exit_code"

[watchx.environment]
""",
        encoding="utf-8",
    )
    return path
