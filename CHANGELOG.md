# Changelog

All notable changes to watchx will be documented here.

## 0.1.0a1 - Unreleased

- Initial project architecture.
- Fullscreen Textual TUI skeleton.
- Rich-based inline renderer for compact mode.
- Direct command execution with optional explicit shell execution.
- Sequential refresh semantics.
- Cancellation and child-process termination.
- Optional diff mode.
- Search and bounded in-memory history.
- Runtime, exit-code, interval, timeout, and output-size metrics.
- TOML configuration.
- CI scaffolding for Windows, Linux, and macOS.
- Shared retry execution with cancellation-aware backoff.
- Improved Windows shell quoting, output decoding, and graceful process termination.
- Intraline diffs, bounded history rendering, and selectable frame details in the TUI.
- Opt-in SQLite invocation storage and configurable alert triggers.
- Regression coverage for the new diff, alert, storage, and configuration paths.
