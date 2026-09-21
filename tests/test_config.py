from pathlib import Path

from watchx.config import WatchConfig, load_config, write_default_config


def test_missing_config_returns_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path / "missing.toml") == WatchConfig()


def test_default_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    write_default_config(path)
    assert load_config(path) == WatchConfig()


def test_extended_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    write_default_config(path)
    config = load_config(path)
    assert config.timeout_seconds is None
    assert config.max_output_bytes == 2_000_000


def test_extended_config_loads_status_and_runtime_options(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[watchx]\nstatus_port = 8765\nretries = 2\nfail_if = "ERROR"\n',
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.status_port == 8765
    assert config.retries == 2
    assert config.fail_if == "ERROR"


def test_status_token_loads_from_config(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[watchx]\nstatus_token = "test-token-with-enough-length"\n',
        encoding="utf-8",
    )

    assert load_config(path).status_token == "test-token-with-enough-length"


def test_invalid_stderr_mode_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[watchx]\nstderr = "nope"\n', encoding="utf-8")

    try:
        load_config(path)
    except ValueError as exc:
        assert "stderr" in str(exc)
    else:
        raise AssertionError("invalid stderr mode was accepted")
