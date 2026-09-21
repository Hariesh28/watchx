from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    print("+", " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    if shutil.which(sys.executable) is None:
        raise SystemExit("Python executable is unavailable")
    run(sys.executable, "-m", "pytest")
    run(sys.executable, "-m", "compileall", "-q", "src", "tests")
    run(sys.executable, "-m", "build")
    artifacts = sorted((ROOT / "dist").glob("*"))
    if not artifacts:
        raise SystemExit("No distribution artifacts were created in dist/")
    run(sys.executable, "-m", "twine", "check", *[str(path) for path in artifacts])
    print("Release checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
