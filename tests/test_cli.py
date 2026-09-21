import pytest

from watchx.cli import build_parser, normalize_command, parse_duration, parse_environment, resolve_config


def test_duration_parser() -> None:
    assert parse_duration("500ms") == 0.5
    assert parse_duration("2s") == 2.0
    assert parse_duration("1m") == 60.0


def test_command_remainder() -> None:
    args = build_parser().parse_args(["--diff", "kubectl", "get", "pods", "-A"])
    assert normalize_command(args.command) == ("kubectl", "get", "pods", "-A")


def test_cli_rejects_invalid_output_limit() -> None:
    args = build_parser().parse_args(["--max-output", "100", "echo", "ok"])

    with pytest.raises(ValueError, match="max output"):
        resolve_config(args)


def test_environment_parser_preserves_values() -> None:
    assert parse_environment(["MODE=production", "TOKEN=a=b"]) == [
        ("MODE", "production"),
        ("TOKEN", "a=b"),
    ]


def test_json_and_retry_options_resolve() -> None:
    args = build_parser().parse_args(["--json", "--retry", "2", "--env", "MODE=test", "echo", "ok"])
    config = resolve_config(args)

    assert config.retries == 2
    assert config.environment == (("MODE", "test"),)


def test_once_option_resolves() -> None:
    args = build_parser().parse_args(["--once", "echo", "ok"])

    assert resolve_config(args).once is True


def test_fail_if_regex_is_validated() -> None:
    args = build_parser().parse_args(["--fail-if", "ERROR", "echo", "ok"])
    assert resolve_config(args).fail_if == "ERROR"

    invalid = build_parser().parse_args(["--fail-if", "[", "echo", "ok"])
    with pytest.raises(ValueError, match="regular expression"):
        resolve_config(invalid)


def test_status_port_is_resolved() -> None:
    args = build_parser().parse_args(["--status-port", "8080", "echo", "ok"])
    assert resolve_config(args).status_port == 8080


def test_status_options_are_validated() -> None:
    short_token = build_parser().parse_args(["--status-token", "too-short", "echo", "ok"])
    with pytest.raises(ValueError, match="status token"):
        resolve_config(short_token)

    invalid_port = build_parser().parse_args(["--status-port", "65536", "echo", "ok"])
    with pytest.raises(ValueError, match="status port"):
        resolve_config(invalid_port)


def test_session_options_resolve(tmp_path) -> None:
    path = tmp_path / "frames.jsonl"
    args = build_parser().parse_args(["--export-session", str(path), "echo", "ok"])
    assert resolve_config(args).export_session == path
