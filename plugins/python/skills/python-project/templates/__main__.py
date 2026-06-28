"""Command-line entry point for myapp.

Kept thin: parse arguments, delegate to importable functions, and translate the
result into a process exit code. Logic lives in sibling modules so tests import
and call it directly instead of shelling out.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code.

    Args:
        argv: Arguments excluding the program name. Defaults to ``sys.argv[1:]``.

    Returns:
        ``0`` on success, non-zero on failure.
    """
    args = sys.argv[1:] if argv is None else argv
    _ = args  # replace with real argument handling
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
