# watchx

**A modern, interactive terminal watch utility.**

`watchx` turns the classic "run this command every N seconds" workflow into a real terminal application: smooth fullscreen rendering, keyboard controls, optional diffs, history, search, live status, and safe sequential command execution.

> The project is alpha software. The initial release is Windows-first, with a portable architecture for Linux and macOS.

## Install

### End users

Python 3.11 or newer is required.

```powershell
py -m pip install watchx
watchx --version
```

If a published package is not available yet, install directly from a checkout:

```powershell
git clone https://github.com/Hariesh28/watchx.git
Set-Location watchx
py -m pip install .
watchx --version
```

### Developers

```powershell
git clone https://github.com/Hariesh28/watchx.git
Set-Location watchx
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -e ".[dev]"
pytest
```

On macOS or Linux, replace activation with `source .venv/bin/activate`.
Use `python -m watchx` if the `watchx` executable is not on `PATH`.

For a complete guide, see [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).
For copy/paste scenarios, see the [`examples/COMMAND_COOKBOOK.md`](examples/COMMAND_COOKBOOK.md).

## Example

```powershell
watchx kubectl get pods -n kube-pulse -o wide
```

Optional diff mode:

```powershell
watchx --diff kubectl get pods -n kube-pulse -o wide
```

Shell execution when you explicitly need shell syntax:

```powershell
watchx --shell powershell "Get-Process | Sort-Object CPU -Descending"
```

## Design goals

- No `Clear-Host` blinking loop.
- Fullscreen TUI by default.
- Generic: works with arbitrary commands.
- Direct process execution is the default; shell invocation is explicit.
- Sequential refreshes: no accidental command pile-up.
- Optional visual diffing rather than modifying the default output.
- Bounded in-memory history.
- Search, pause, manual refresh, interval controls, mouse support, and help.
- Windows-first without baking Windows-only assumptions into the core.
- Modern packaging with `pyproject.toml`, testable modules, and CI-ready tooling.

## Quick reference

```text
watchx [OPTIONS] COMMAND [ARGUMENTS...]
```

The command is executed directly by default. Put `--` before a command when
its first argument could be interpreted as a watchx option.

## Development

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
pytest
```

Run from the source tree:

```powershell
watchx python -c "import time; [print(time.time()) or time.sleep(1) for _ in range(100)]"
```

PowerShell pipelines are explicit shell commands:

```powershell
watchx --shell powershell "Get-Process | Sort-Object CPU -Descending"
```

For a compact embedded display:

```powershell
watchx --inline kubectl get pods -n kube-pulse -o wide
```

Useful safety/behavior flags:

```powershell
watchx -i 500ms --diff --stderr separate --timeout 10s kubectl get pods -A
```

Run one refresh and return a useful process exit code:

```powershell
watchx --once --plain python -c "print('ready')"
```

Structured output for automation:

```powershell
watchx --json --plain --timestamp --retry 2 --env ENV=production curl https://example.com
```

`--json` emits one object per refresh with `stdout`, `stderr`, `exit_code`,
`duration_ms`, `started_at`, `timed_out`, `ok`, and `sequence` fields.
`--retry` retries failed invocations before publishing the final result, and
`--env KEY=VALUE` adds environment variables without replacing the parent environment.
Use `--fail-if REGEX` to mark matching output as unhealthy; JSON frames include
`alert_triggered`, and `--once` returns exit code 1 when the alert matches.

Expose the latest result to local monitors:

```powershell
$token = "replace-with-a-secret-at-least-16-characters"
watchx --status-port 8765 --status-token $token --json --plain kubectl get pods -A
curl.exe -H "Authorization: Bearer $token" http://127.0.0.1:8765/health
curl.exe -H "Authorization: Bearer $token" http://127.0.0.1:8765/metrics
```

The opt-in server binds to localhost and shuts down with watchx. Both endpoints
return the latest machine-readable status snapshot without command stdout or
stderr, so secrets emitted by watched commands are not exposed through health
or metrics endpoints. Endpoints require a bearer token; watchx prints an
automatically generated token to stderr, or use `--status-token` to provide
your own token.

Save and replay a session:

```powershell
watchx --once --export-session .\run.jsonl --plain kubectl get pods -A
watchx --replay .\run.jsonl --replay-delay 500ms
```

Session files are UTF-8 JSONL records containing captured output, timing,
status, and frame metadata. They can be archived or processed with standard
JSON tooling.

## Configuration

Create a starter configuration file with:

```powershell
watchx --init-config
```

The file is stored at `%APPDATA%\watchx\config.toml` on Windows,
`~/Library/Application Support/watchx/config.toml` on macOS, or
`$XDG_CONFIG_HOME/watchx/config.toml` (defaulting to `~/.config/watchx`) on Linux.
Command-line options override values from this file.

## Documentation

- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md): installation, usage, options, configuration, automation, troubleshooting, and development.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): code structure and execution flow.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): planned work.
- [`examples/COMMAND_COOKBOOK.md`](examples/COMMAND_COOKBOOK.md): detailed command examples for local checks, shells, Kubernetes, automation, alerts, status, and sessions.

## License

MIT
