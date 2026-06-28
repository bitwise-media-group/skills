"""Generate a reproducible markdown CLI reference from a Click or Typer command.

Usage:
    uv run python -m myapp.tools.docgen --out docs/cli

Writes one markdown page per command (``myapp.md``, ``myapp_serve.md``, ...) that
humans and LLMs can read. Output is timestamp-free, so the
committed reference changes only when commands or flags change.

Typer apps convert to a Click command with ``typer.main.get_command(app)``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import click

# Point this at your CLI command. For a Click app this is the `click.Group`/
# `click.Command`; for Typer use:
#     from typer.main import get_command
#     from myapp.cli import app
#     cli = get_command(app)
from myapp.cli import cli


def page(command: click.Command, ctx: click.Context, path: list[str]) -> str:
    """Render a single command's help as a markdown page."""
    title = " ".join(path)
    machine_data = {
        "path": path,
        "name": command.name,
        "help": command.help or "",
        "help_short": command.get_short_help_str(80),
        "is_hidden": command.hidden,
        "options": [],
        "arguments": [],
        "subcommands": [],
    }
    for param in command.params:
        if isinstance(param, click.Argument):
            machine_data["arguments"].append(
                {
                    "name": param.name,
                    "metavar": param.make_metavar(),
                    "required": param.required,
                    "nargs": param.nargs,
                    "type": getattr(param.type, "name", type(param.type).__name__),
                    "help": param.help or "",
                }
            )
            continue

        if isinstance(param, click.Option):
            machine_data["options"].append(
                {
                    "name": param.name,
                    "aliases": sorted(param.opts + param.secondary_opts),
                    "help": param.help or "",
                    "required": param.required,
                    "is_flag": param.is_flag,
                    "default": None if param.default is None else str(param.default),
                    "type": getattr(param.type, "name", type(param.type).__name__),
                    "metavar": param.make_metavar(),
                    "envvar": param.envvar,
                }
            )

    if isinstance(command, click.Group):
        for name in sorted(command.list_commands(ctx)):
            machine_data["subcommands"].append(name)

    body = command.get_help(ctx).strip()
    lines: list[str] = [
        f"# {title}",
        "",
        "## Machine-readable summary",
        "```json",
        json.dumps(machine_data, indent=2),
        "```",
        "",
        "## Click help",
        "```text",
        body,
        "```",
        "",
    ]
    return "\n".join(lines)


def walk(
    command: click.Command,
    path: list[str],
    parent: click.Context | None,
    out: Path,
) -> None:
    """Write ``command`` and recurse into subcommands of a group."""
    ctx = click.Context(command, info_name=command.name, parent=parent)
    out.joinpath(f"{'_'.join(path)}.md").write_text(page(command, ctx, path), encoding="utf-8")
    if isinstance(command, click.Group):
        for name in sorted(command.list_commands(ctx)):
            sub = command.get_command(ctx, name)
            if sub is not None and not sub.hidden:
                walk(sub, [*path, name], ctx, out)


def main() -> int:
    """Generate the CLI reference tree and return an exit code."""
    parser = argparse.ArgumentParser(description="Generate the markdown CLI reference.")
    parser.add_argument("--out", type=Path, default=Path("docs/cli"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    walk(cli, [cli.name or "cli"], None, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
