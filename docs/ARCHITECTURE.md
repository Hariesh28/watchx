# watchx architecture

```text
CLI
 │
 ├── config loader ────────┐
 │                         │
 └── CommandSpec            │
            │               │
            ▼               ▼
       CommandRunner     WatchConfig
            │
            ▼
       CommandResult
            │
            ▼
        Frame model
         ┌──┴───┐
         ▼      ▼
      History  Diff engine
         │      │
         └──┬───┘
            ▼
       Presentation
       ┌───────────────┐
       │ Textual TUI   │  fullscreen Windows-first
       │ Rich Live     │  inline/compact fallback
       └───────────────┘
```

## Execution model

One refresh produces one immutable `CommandResult` and one immutable `Frame`. The next refresh does not start until the previous invocation has completed. UI work stays on the Textual event loop; blocking subprocess work executes in a worker thread.

## Why not one renderer?

Textual is the primary interactive application framework. Its application mode is ideal for a true fullscreen TUI, but Textual's built-in inline mode is currently not supported on Windows. The compact `--inline` path therefore uses Rich Live instead of pretending both modes are equivalent.

## Rendering contract

The renderer receives frames, not subprocesses. This keeps command execution separate from UI presentation and lets future structured renderers consume the same frame model.
