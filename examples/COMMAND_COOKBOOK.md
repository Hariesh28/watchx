# watchx Command Cookbook

These examples are copy/paste starting points. Commands use PowerShell syntax
where applicable; on macOS and Linux, replace PowerShell continuation
backticks with a single line or a shell continuation.

## 1. Start with a local command

Run a command every two seconds in the fullscreen TUI:

```powershell
watchx Get-Date
```

Use a shorter interval and show output changes:

```powershell
watchx --interval 500ms --diff Get-Date
```

Use `q` or `Ctrl+C` to stop. Press `p` to pause, `r` to refresh immediately,
`d` to toggle diff mode, `/` to search, and `h` to inspect history.

## 2. Monitor development tools

Watch a directory and show the newest files:

```powershell
watchx --shell powershell "Get-ChildItem .\build -File | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,Length,LastWriteTime"
```

Monitor running processes:

```powershell
watchx --shell powershell "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name,CPU,Id"
```

Monitor a local HTTP endpoint:

```powershell
watchx --interval 5s --shell powershell "try { (Invoke-WebRequest http://127.0.0.1:8080/health -UseBasicParsing).StatusCode } catch { $_.Exception.Message; exit 1 }"
```

## 3. Kubernetes and containers

Watch all Kubernetes pods with diffs:

```powershell
watchx --interval 5s --diff kubectl get pods --all-namespaces -o wide
```

Stop on the first failed Kubernetes check:

```powershell
watchx --interval 10s --exit-on-error --stderr separate kubectl get deployment api -n production
```

Watch Docker containers:

```powershell
watchx --inline --interval 3s docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## 4. Explicit shell features

PowerShell pipelines and formatting:

```powershell
watchx --shell powershell "Get-Service | Where-Object Status -eq 'Running' | Sort-Object DisplayName | Format-Table -AutoSize"
```

PowerShell environment variables:

```powershell
watchx --shell powershell '$env:APP_ENV; Get-Date -Format "yyyy-MM-dd HH:mm:ss"'
```

Windows `cmd` built-ins:

```powershell
watchx --shell cmd "set STATUS=ready && echo %STATUS%"
```

Bash pipelines on systems with Bash installed:

```powershell
watchx --shell bash "printf '%s\n' \"$HOME\" | tr a-z A-Z"
```

Shell execution is explicit. Direct execution is the default and avoids shell
parsing when it is not needed.

## 5. One-shot checks and exit codes

Run exactly once and print only command output:

```powershell
watchx --once --plain python -c "print('deployment ready')"
```

Add a timeout and retries for a flaky external check:

```powershell
watchx --once --plain --timeout 15s --retry 3 curl.exe https://example.com
```

The command's exit code is returned for process failures. A successful command
that matches `--fail-if` returns `1`.

## 6. Structured JSON automation

Emit one JSON object per refresh:

```powershell
watchx --json --plain --timestamp --interval 30s kubectl get nodes -o json
```

Save the stream while still seeing it:

```powershell
watchx --json --plain --interval 10s kubectl get pods -A |
  Tee-Object -FilePath .\watchx-frames.jsonl
```

Set environment variables only for the watched process:

```powershell
watchx --once --plain --env APP_ENV=staging --env REGION=eu-west-1 `
  python -c "import os; print(os.environ['APP_ENV'], os.environ['REGION'])"
```

## 7. Alerts and failure policies

Fail when output contains an unhealthy Kubernetes state:

```powershell
watchx --once --plain --fail-if "CrashLoopBackOff|ImagePullBackOff|Error" `
  kubectl get pods -A
```

Stop a continuous watch when output matches an alert:

```powershell
watchx --interval 5s --exit-on-error --fail-if "CRITICAL|FAILED" `
  --shell powershell "Get-Content .\application.log -Tail 100"
```

Keep stderr visible separately while checking it too:

```powershell
watchx --once --stderr separate --fail-if "timeout|refused" `
  curl.exe https://api.example.com/health
```

## 8. Health and metrics endpoints

Start an authenticated localhost status endpoint:

```powershell
$token = "replace-with-a-secret-at-least-16-characters"
watchx --status-port 8765 --status-token $token --interval 5s `
  --json --plain kubectl get pods -A
```

Query it from another terminal:

```powershell
curl.exe -H "Authorization: Bearer $token" http://127.0.0.1:8765/health
curl.exe -H "Authorization: Bearer $token" http://127.0.0.1:8765/metrics
```

Status responses contain operational metadata only. Captured command output is
not returned by these endpoints. If no token is supplied, watchx generates
one and prints it to stderr; treat it as a secret.

## 9. Sessions and replay

Capture one result for later inspection:

```powershell
watchx --once --plain --export-session .\health-check.jsonl `
  curl.exe https://example.com/health
```

Capture bounded history from a continuous TUI session:

```powershell
watchx --history-size 500 --export-session .\deployment.jsonl `
  kubectl get pods -A
```

Replay without executing the original command:

```powershell
watchx --replay .\deployment.jsonl --replay-delay 500ms
```

Session files contain command output and may contain secrets. Store them with
the same care as application logs.

## 10. Configuration-driven usage

Create the starter configuration:

```powershell
watchx --init-config
```

Then place reusable defaults in the generated TOML file and run a command:

```powershell
watchx --diff --timeout 10s kubectl get pods -A
```

Command-line options override configuration-file values. Use `watchx --help`
to see every option and its accepted format.
