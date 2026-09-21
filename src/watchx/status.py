from __future__ import annotations

import json
import hmac
import secrets
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import Any


class StatusServer:
    """Optional localhost health and metrics server without command output."""

    def __init__(self, port: int, snapshot: Callable[[], dict[str, Any]], token: str | None = None) -> None:
        self._snapshot = snapshot
        self.token = token or secrets.token_urlsafe(32)
        if len(self.token) < 16:
            raise ValueError("status token must be at least 16 characters")
        self._lock = Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", port), self._handler())
        self._thread: Thread | None = None

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = Thread(target=self._server.serve_forever, name="watchx-status", daemon=True)
        self._thread.start()

    def close(self) -> None:
        if self._thread is not None:
            self._server.shutdown()
            self._thread.join(timeout=2)
            self._thread = None
        self._server.server_close()

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path not in {"/health", "/metrics"}:
                    self.send_error(404)
                    return
                authorization = self.headers.get("Authorization", "")
                supplied = authorization.removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied, owner.token):
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", "Bearer")
                    self.end_headers()
                    return
                with owner._lock:
                    payload = owner._public_snapshot(self.path, owner._snapshot())
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        return Handler

    @staticmethod
    def _public_snapshot(path: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "ok",
            "running",
            "sequence",
            "exit_code",
            "duration_ms",
            "timed_out",
            "alert_triggered",
        }
        payload = {key: value for key, value in snapshot.items() if key in allowed}
        payload["endpoint"] = path[1:]
        return payload
