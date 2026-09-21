# watchx User Guide

`watchx` repeatedly runs a command, captures its output, and presents the latest
result without the flicker of a clear-and-print loop. It is useful for cluster
status, build monitoring, local development, deployment checks, and lightweight
automation.

## 1. Requirements

- Python 3.11 or newer.
- A terminal that supports standard ANSI output for the best TUI experience.
- The command being watched must be available on `PATH`, or be passed with an
  absolute path.
- PowerShell users should use PowerShell 5.1 or PowerShell 7. Bash and `cmd`
  support are available where those shells are installed.

## 2. Installation

### Install from PyPI

```powershell
py -m pip install watchx
watchx --version
```

### Install from source

```powershell
git clone https://github.com/Hariesh28/watchx.git
Set-Location watchx
py -m pip install .
```

### Editable development install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
pytest
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Basic usage

The simplest invocation runs in the fullscreen TUI:

```powershell
watchx Get-Date
watchx kubectl get pods -A
watchx -i 5s ping localhost
```

Durations accept milliseconds, seconds, minutes, hours, or a unitless number
of seconds:

```text
500ms  2s  1.5m  1h  10
```

The interval must be greater than zero. Refreshes are sequential: a new
invocation does not start while the previous invocation is still running.

## 4. TUI controls

| Key | Action |
|---|---|
| `q` or `Ctrl+C` | Quit |
| `r` | Refresh immediately |
| `p` | Pause or resume scheduled refreshes |
| `+`, `=` | Make the interval faster |
| `-` | Make the interval slower |
| `0` | Reset interval to 2 seconds |
| `d` | Toggle line diff mode |
| `/` | Search the current output |
| `Esc` | Close search |
| `h` | Open frame history |
| `?` | Open help |

Use `--no-mouse` when running in a terminal where mouse reporting causes
problems.

## 5. Output modes

### Fullscreen TUI

This is the default:

```powershell
watchx --diff --stderr separate kubectl get pods -A
```

### Inline mode

Use this when embedding watchx in an existing terminal layout:

```powershell
watchx --inline -i 2s docker ps
```

### Plain mode

Plain mode is intended for logs and simple terminal automation:

```powershell
watchx --plain --timestamp -i 10s Get-Date
```

### One-shot mode

`--once` executes exactly one refresh and exits. It returns `0` for a healthy
command and the command's non-zero exit code for a failed command:

```powershell
watchx --once --plain python -c "print('deployment ready')"
```

## 6. Shell commands

Direct process execution is the default and is safer because no shell parser is
involved. Use `--shell` only when you need pipelines, redirection, variables,
or shell built-ins:

```powershell
watchx --shell powershell "Get-Process | Sort-Object CPU -Descending"
watchx --shell pwsh "Get-Date -Format 'HH:mm:ss.fff'"
watchx --shell cmd "set STATUS=ready && echo %STATUS%"
watchx --shell bash "printf '%s\n' \"$HOME\" | tr a-z A-Z"
```

When using a shell, quote the complete shell command as one argument. Shell
syntax is intentionally passed through to that shell.

## 7. Errors, timeouts, retries, and output

```powershell
watchx --timeout 10s --retry 3 --exit-on-error curl https://example.com
```

- `--timeout` terminates an invocation that exceeds the limit.
- `--retry N` retries failed invocations before publishing the final result.
- `--exit-on-error` stops continuous watching after a failed result.
- `--max-output N` bounds captured stdout and stderr in bytes.
- `--stderr combined` merges streams, `separate` adds a delimiter, and
  `hidden` omits stderr from displayed output.

## 8. JSON and automation

JSON mode writes one JSON object per refresh and is suitable for pipelines:

```powershell
watchx --json --plain --once kubectl get pods -A
```

Each frame contains:

| Field | Meaning |
|---|---|
| `stdout` | Captured standard output |
| `stderr` | Captured standard error |
| `exit_code` | Process exit code |
| `duration_ms` | Execution duration |
| `started_at` | ISO-8601 start timestamp |
| `timed_out` | Whether the timeout ended the process |
| `ok` | Whether the result is healthy |
| `sequence` | Refresh number |
| `alert_triggered` | Whether `--fail-if` matched |

Example PowerShell pipeline:

```powershell
watchx --json --plain -i 30s --status-port 8765 kubectl get pods -A |
  Tee-Object -FilePath .\watchx.jsonl
```

## 9. Alerts

Fail a result when output matches a regular expression:

```powershell
watchx --once --json --fail-if "CrashLoopBackOff|ERROR" kubectl get pods -A
```

Matching output sets `alert_triggered` to `true`, makes the JSON result
unhealthy, and returns exit code `1` in one-shot mode. Matching uses the
configured stderr mode.

## 10. Environment variables

Add or override variables for the watched command without changing the parent
shell:

```powershell
watchx --once --plain --env APP_ENV=staging --env REGION=eu-west-1 `
  python -c "import os; print(os.environ['APP_ENV'])"
```

Values may contain additional equals signs, for example
`--env TOKEN=part1=part2`.

## 11. Health and metrics endpoints

Start the optional localhost-only status server:

```powershell
watchx --status-port 8765 --json --plain kubectl get pods -A
```

Query it from another terminal:

```powershell
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/metrics
```

Both endpoints return the latest machine-readable snapshot. Use
`--status-port 0` to choose an available ephemeral port in application code;
for shell monitoring, use a fixed port. The server binds only to `127.0.0.1`
and is disabled unless `--status-port` is supplied. Health and metrics never
return captured stdout or stderr; use JSON output or session export when you
explicitly need command contents. Requests require `Authorization: Bearer
TOKEN`. watchx prints a cryptographically random token to stderr at startup;
for automation, provide a stable token with `--status-token` or
`status_token` in the config file:

```powershell
$token = "replace-with-a-secret-at-least-16-characters"
watchx --status-port 8765 --status-token $token --plain Get-Date
curl.exe -H "Authorization: Bearer $token" http://127.0.0.1:8765/health
```

## 12. Sessions and replay

Export captured frames as newline-delimited JSON:

```powershell
watchx --export-session .\deployment.jsonl --once --plain kubectl get pods -A
```

For a continuous watch, press `q` to exit and write the bounded in-memory
history to the export path:

```powershell
watchx --history-size 500 --export-session .\deployment.jsonl kubectl get pods -A
```

Replay a saved session without executing the original command:

```powershell
watchx --replay .\deployment.jsonl --replay-delay 500ms
```

Replay returns `0` when the final saved frame was healthy and `1` otherwise.
Session records include stdout, stderr, exit status, duration, timestamps,
sequence numbers, and rendered lines. Do not store sessions in shared
locations if command output may contain secrets.

## 13. Configuration

Create a starter file:

```powershell
watchx --init-config
```

Locations:

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\watchx\config.toml` |
| macOS | `~/Library/Application Support/watchx/config.toml` |
| Linux | `$XDG_CONFIG_HOME/watchx/config.toml`, or `~/.config/watchx/config.toml` |

Example:

```toml
[watchx]
interval_seconds = 5.0
diff = true
mouse = true
theme = "watchx-dark"
history_size = 100
fullscreen = true
shell = ""
stderr = "separate"
exit_on_error = false
timeout_seconds = 10.0
max_output_bytes = 2000000
retries = 2
timestamp = true
fail_if = "ERROR|CRITICAL"
status_port = 8765
status_token = "replace-with-a-secret-at-least-16-characters"

[watchx.environment]
APP_ENV = "staging"
REGION = "eu-west-1"
```

CLI arguments override configuration values. Invalid intervals, ports, retry
counts, stderr modes, output limits, and regular expressions are rejected
before a command starts.

## 14. Troubleshooting

### `watchx` is not recognized

Activate the virtual environment or invoke the module directly:

```powershell
.\.venv\Scripts\Activate.ps1
python -m watchx --version
```

### A shell command does not work

Make sure the shell is explicit and the whole expression is quoted:

```powershell
watchx --shell powershell "Get-ChildItem | Select-Object Name"
```

### Output is cut off

Increase the limit:

```powershell
watchx --max-output 10000000 --once --plain your-command
```

### A command keeps running

Set a timeout. watchx terminates the process tree when the timeout is reached:

```powershell
watchx --timeout 30s your-command
```

### The TUI is not rendering correctly

Try a simpler renderer:

```powershell
watchx --plain your-command
watchx --inline your-command
```

## 15. Development checks

From an activated development environment:

```powershell
pytest
python -m compileall -q src tests
python scripts/release_check.py
```

The implementation is organized around `cli.py`, `runner.py`, `models.py`,
`config.py`, `inline.py`, `status.py`, and `tui/`. See
[`ARCHITECTURE.md`](ARCHITECTURE.md) for the execution flow.

The release check requires the `build` and `twine` development tools and
produces validated artifacts in `dist/`. Do not commit `dist/`; it is ignored
by the repository.
