import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from watchx.status import StatusServer


def test_status_server_serves_health_and_metrics() -> None:
    server = StatusServer(
        0,
        lambda: {
            "ok": True,
            "sequence": 4,
            "stdout": "secret-token",
            "stderr": "private-error",
            "duration_ms": 12.5,
        },
        token="test-token-with-enough-length",
    )
    server.start()
    try:
        for path in ("/health", "/metrics"):
            request = Request(
                f"http://127.0.0.1:{server.port}{path}",
                headers={"Authorization": f"Bearer {server.token}"},
            )
            with urlopen(request, timeout=2) as response:
                assert response.status == 200
                payload = json.loads(response.read())
                assert payload["sequence"] == 4
                assert payload["duration_ms"] == 12.5
                assert "stdout" not in payload
                assert "stderr" not in payload
                assert "secret-token" not in json.dumps(payload)
                assert "private-error" not in json.dumps(payload)
    finally:
        server.close()


def test_status_server_requires_bearer_token() -> None:
    server = StatusServer(0, lambda: {"ok": True}, token="test-token-with-enough-length")
    server.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{server.port}/health", timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("unauthenticated status request was accepted")
    finally:
        server.close()


def test_status_server_rejects_wrong_bearer_token() -> None:
    server = StatusServer(0, lambda: {"ok": True}, token="test-token-with-enough-length")
    server.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.port}/health",
            headers={"Authorization": "Bearer wrong-token-with-enough-length"},
        )
        try:
            urlopen(request, timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
            assert exc.headers["WWW-Authenticate"] == "Bearer"
        else:
            raise AssertionError("invalid status token was accepted")
    finally:
        server.close()


def test_status_server_rejects_unknown_paths() -> None:
    server = StatusServer(0, lambda: {})
    server.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{server.port}/unknown", timeout=2)
        except Exception as exc:
            assert "HTTP Error 404" in str(exc)
        else:
            raise AssertionError("unknown status path was accepted")
    finally:
        server.close()
