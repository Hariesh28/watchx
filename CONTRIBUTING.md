# Contributing to watchx

## Development setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
python scripts/release_check.py
```

`scripts/release_check.py` runs the test suite, compiles the package, builds
both wheel and source distributions, and validates distribution metadata with
Twine. Run it from an environment with the development extras installed.

The release workflow runs the same package validation on every CI pass before
publishing. Create a GitHub Release to trigger the PyPI publish workflow.

## Principles

- Keep command execution separate from rendering.
- Keep the default experience simple and non-destructive.
- Prefer explicit behavior for shell execution and potentially expensive operations.
- Add tests for core behavior before changing public CLI semantics.
- Preserve Windows behavior while keeping platform-specific code isolated.
