# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT
"""Generate the docs site's plugin, skill and evaluation pages.

The skills, manifests and evolve reports are the source of truth; this script
renders them into the Zensical tree, the same way dotty generates docs/cli from
its cobra command tree. It owns these outputs outright (rewrites them and
prunes stale files), so they must never be edited by hand:

    docs/plugins/**                         plugin, skill and reference pages
    docs/evaluation.md                      EVALUATION.md, cross-linked
    overrides/partials/plugin-cards.html    landing: the plugin grid
    overrides/partials/eval-stats.html      landing: the evaluation stat row

Usage (stdlib only, Python >= 3.11 for tomllib):

    uv run python scripts/gen-docs.py           # regenerate in place
    uv run python scripts/gen-docs.py --check   # regenerate into $TMPDIR, diff

Both modes also load zensical.toml and fail when a generated page is missing
from `nav` (or `nav` points at a generated page that no longer exists), so a
new skill or plugin can't silently drop out of the site.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/bitwise-media-group/skills"
BRANCH = "main"
MARKETPLACE = "bitwise"

# Outputs owned by this script, relative to the repo root.
OWNED_DIRS = ["docs/plugins"]
OWNED_FILES = [
    "docs/evaluation.md",
    "overrides/partials/plugin-cards.html",
    "overrides/partials/eval-stats.html",
]

HTML_LICENSE = "<!--\n Copyright 2026 Bitwise Media Group\n SPDX-License-Identifier: MIT\n-->\n"
PROVIDERS = {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google", "xai": "xAI", "cursor": "Cursor"}

FENCE = re.compile(r"^\s*(```+|~~~+)")
CODE_SPAN = re.compile(r"(`+)(?!`).+?(?<!`)\1(?!`)")
LINK = re.compile(r"(!?\[[^\]]*\])\(([^()\s]+)((?:\s+\"[^\"]*\")?)\)")


# ---------------------------------------------------------------- model ----


@dataclass
class Skill:
    name: str
    description: str
    src: Path  # skill directory, relative to ROOT
    body: str
    has_reference: bool


@dataclass
class Command:
    name: str
    description: str


@dataclass
class Plugin:
    name: str
    description: str
    keywords: list[str]
    version: str
    skills: list[Skill] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a Markdown file into flat string frontmatter and body.

    Handles the two shapes this repo uses: single-line `key: value` (the skill
    policy) and prettier-folded scalars (`key:` then indented continuation
    lines, as in the Claude command files).
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.index("\n---\n", 4)
    meta: dict[str, str] = {}
    key = None
    for line in text[4:end].splitlines():
        if line[:1] in (" ", "\t") and key:
            meta[key] = (meta[key] + " " + line.strip()).strip()
            continue
        k, _, v = line.partition(":")
        key = k.strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[key] = v
    return meta, text[end + 5 :].lstrip("\n")


def load_plugins() -> list[Plugin]:
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    plugins = []
    for entry in market["plugins"]:
        pdir = ROOT / entry["source"]
        manifest = json.loads((pdir / ".claude-plugin/plugin.json").read_text())
        plugin = Plugin(
            name=entry["name"],
            description=entry["description"],
            keywords=entry.get("keywords", []),
            version=manifest["version"],
        )
        for sdir in sorted(p.parent for p in pdir.glob("skills/*/SKILL.md")):
            meta, body = parse_frontmatter((sdir / "SKILL.md").read_text())
            plugin.skills.append(
                Skill(
                    name=meta.get("name", sdir.name),
                    description=meta.get("description", ""),
                    src=sdir.relative_to(ROOT),
                    body=body,
                    has_reference=(sdir / "reference.md").is_file(),
                )
            )
        for cmd in sorted(pdir.glob("commands/*.md")):
            meta, _ = parse_frontmatter(cmd.read_text())
            plugin.commands.append(Command(name=cmd.stem, description=meta.get("description", "")))
        plugins.append(plugin)
    return plugins


def first_sentence(text: str) -> str:
    """The description up to its first sentence break or em-dash elaboration."""
    m = re.search(r"[.!?](\s|$)", text)
    end = m.start() + 1 if m else len(text)
    # the first em-dash outside parentheses
    dash, depth = -1, 0
    for i, ch in enumerate(text[:end]):
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and text.startswith(" — ", i):
            dash = i
            break
    if dash >= 0:
        return text[:dash].rstrip(" ,;:") + "."
    return text[:end]


def pct(rate: float) -> str:
    return f"{rate * 100:.0f}%"


def provider_name(model_id: str, entry: dict) -> str:
    prov = entry.get("provider") or model_id.split("/", 1)[0]
    return PROVIDERS.get(prov, prov)


# -------------------------------------------------------------- linking ----


class Linker:
    """Rewrites relative links in rendered Markdown.

    A link whose target is another rendered source (a SKILL.md, reference.md,
    or EVALUATION.md) is pointed at that source's generated page; a link to a
    repo file that isn't rendered (templates/, tflint.hcl, …) becomes a GitHub
    URL; a link to something that doesn't exist is left alone. Backticked
    sibling-skill names are auto-linked to their pages. Fenced blocks and
    inline code spans are never rewritten.
    """

    def __init__(self, plugins: list[Plugin]):
        self.pages: dict[str, str] = {"EVALUATION.md": "docs/evaluation.md"}
        self.skill_pages: dict[str, str] = {}
        for p in plugins:
            self.pages[f"plugins/{p.name}/EVALUATION.md"] = f"docs/plugins/{p.name}/evaluation.md"
            for s in p.skills:
                page = f"docs/plugins/{p.name}/{s.name}/index.md"
                self.pages[f"{s.src.as_posix()}/SKILL.md"] = page
                self.pages[f"{s.src.as_posix()}/reference.md"] = f"docs/plugins/{p.name}/{s.name}/reference.md"
                self.skill_pages[s.name] = page

    @staticmethod
    def rel(from_page: str, to_page: str) -> str:
        return posixpath.relpath(to_page, posixpath.dirname(from_page))

    def target(self, src_file: str, out_page: str, href: str) -> str:
        if re.match(r"^[a-z][a-z0-9+.-]*:", href) or href.startswith(("#", "/")):
            return href
        path, _, anchor = href.partition("#")
        if not path:
            return href
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(src_file), path))
        anchor = f"#{anchor}" if anchor else ""
        if resolved in self.pages:
            return self.rel(out_page, self.pages[resolved]) + anchor
        full = ROOT / resolved
        if resolved.startswith("..") or not full.exists():
            return href
        kind = "tree" if full.is_dir() else "blob"
        return f"{REPO_URL}/{kind}/{BRANCH}/{resolved}{anchor}"

    def link(self, m: re.Match, src_file: str, out_page: str) -> str:
        return f"{m.group(1)}({self.target(src_file, out_page, m.group(2))}{m.group(3)})"

    def autolink(self, span: str, out_page: str, self_skill: str | None) -> str:
        m = re.fullmatch(r"`([a-z0-9-]+)`", span)
        if not m or m.group(1) not in self.skill_pages or m.group(1) == self_skill:
            return span
        return f"[{span}]({self.rel(out_page, self.skill_pages[m.group(1)])})"

    def render_line(self, line: str, src_file: str, out_page: str, self_skill: str | None) -> str:
        # Links are rewritten unless they start inside a code span; then a code
        # span that is exactly a sibling skill's name — outside any link — is
        # turned into a link to that skill's page (never in headings).
        def spans(text: str) -> list[tuple[int, int]]:
            return [m.span() for m in CODE_SPAN.finditer(text)]

        def inside(i: int, ranges: list[tuple[int, int]]) -> bool:
            return any(a <= i < b for a, b in ranges)

        code = spans(line)
        line = LINK.sub(
            lambda m: m.group(0) if inside(m.start(), code) else self.link(m, src_file, out_page),
            line,
        )
        if line.lstrip().startswith("#"):
            return line
        code = spans(line)
        links = [m.span() for m in LINK.finditer(line) if not inside(m.start(), code)]
        out, pos = [], 0
        for a, b in code:
            out.append(line[pos:a])
            span = line[a:b]
            out.append(span if inside(a, links) else self.autolink(span, out_page, self_skill))
            pos = b
        out.append(line[pos:])
        return "".join(out)

    def render(self, text: str, src_file: str, out_page: str, self_skill: str | None = None) -> str:
        out, in_fence, fence = [], False, ""
        for line in text.split("\n"):
            m = FENCE.match(line)
            if m:
                tok = m.group(1)
                if not in_fence:
                    in_fence, fence = True, tok[0] * len(tok)
                elif tok.startswith(fence):
                    in_fence = False
                out.append(line)
                continue
            if in_fence:
                out.append(line)
                continue
            out.append(self.render_line(line, src_file, out_page, self_skill))
        return "\n".join(out)


# ------------------------------------------------------------ rendering ----


def front_matter(**kv: str) -> str:
    lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in kv.items()] + ["---", ""]
    return "\n".join(lines)


def generated_note(src: str) -> str:
    return f"<!-- Generated by scripts/gen-docs.py from {src}; do not edit by hand. Regenerate with: make docs-gen -->\n"


def insert_after_h1(body: str, block: str) -> str:
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return "\n".join(lines[: i + 1] + ["", block.rstrip("\n")] + lines[i + 1 :])
        if line.strip():
            break
    return block + "\n" + body


def gh(path: str, kind: str = "blob") -> str:
    return f"{REPO_URL}/{kind}/{BRANCH}/{path}"


def eval_rows(plugin_eval: dict) -> list[tuple[str, str, dict, dict]]:
    """(provider, model id, triggers entry, evals entry) sorted by provider, model."""
    models = sorted(set(plugin_eval.get("triggers", {})) | set(plugin_eval.get("evals", {})))
    rows = []
    for mid in models:
        t = plugin_eval.get("triggers", {}).get(mid, {})
        e = plugin_eval.get("evals", {}).get(mid, {})
        rows.append((provider_name(mid, t or e), mid, t, e))
    return rows


def rate_cell(entry: dict) -> str:
    if not entry or not entry.get("total"):
        return "—"
    return f"{pct(entry['pass_rate'])} ({entry['passed']}/{entry['total']})"


def render_eval_table(plugin_eval: dict) -> str:
    out = [
        "| Provider | Model | Trigger accuracy | Behavioral (with skill) | Baseline (no skill) | Lift |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for prov, mid, t, e in eval_rows(plugin_eval):
        display = (t or e).get("display", mid)
        base = e.get("baseline", {}) if e else {}
        lift = "—"
        if e and base.get("total"):
            delta = e["pass_rate"] - base["pass_rate"]
            lift = f"{'+' if delta >= 0 else '−'}{abs(delta) * 100:.0f} pts"
        out.append(f"| {prov} | {display} | {rate_cell(t)} | {rate_cell(e)} | {rate_cell(base)} | {lift} |")
    return "\n".join(out)


def render_plugin_index(p: Plugin, evaluation: dict, linker: Linker) -> str:
    page = f"docs/plugins/{p.name}/index.md"
    src = f"plugins/{p.name}"
    parts = [
        front_matter(title=p.name, description=p.description),
        generated_note(f"{src}/ (manifests, SKILL.md frontmatter, EVALUATION.json)"),
        f"# {p.name}",
        "",
        '<div class="bw-skillhead">',
        f'<p class="bw-skillhead__desc">{html.escape(p.description)}</p>',
        '<div class="bw-skillhead__meta">',
        f'<span class="bw-badge">v{p.version}</span>',
        f'<span class="bw-skillhead__count">{len(p.skills)} skills</span>',
        f'<a href="{gh(src, "tree")}">Browse <code>{src}/</code> on GitHub</a>',
        "</div>",
        "</div>",
        "",
        "## Install",
        "",
        '=== "Claude Code"',
        "",
        "    ```text",
        f"    /plugin marketplace add bitwise-media-group/skills",
        f"    /plugin install {p.name}@{MARKETPLACE}",
        "    ```",
        "",
        '=== "Codex CLI"',
        "",
        "    ```sh",
        "    codex plugin marketplace add bitwise-media-group/skills",
        f"    codex plugin add {p.name}@{MARKETPLACE}",
        "    ```",
        "",
        '=== "OpenCode / Antigravity"',
        "",
        "    ```sh",
        "    git clone https://github.com/bitwise-media-group/skills",
        "    ./skills/install.sh --global   # links every skill, this plugin's included",
        "    ```",
        "",
        "See [Install](../../install.md) for scopes and options.",
        "",
        "## Skills",
        "",
        "| Skill | What it does |",
        "| --- | --- |",
    ]
    for s in p.skills:
        desc = first_sentence(s.description).replace("|", "\\|")
        parts.append(f"| [`{s.name}`]({linker.rel(page, linker.skill_pages[s.name])}) | {desc} |")
    if p.commands:
        parts += ["", "## Commands", "", "Claude Code slash commands — thin entry points to the skills above.", ""]
        parts += ["| Command | What it does |", "| --- | --- |"]
        for c in p.commands:
            parts.append(f"| `/{p.name}:{c.name}` | {c.description.replace('|', chr(92) + '|')} |")
    parts += ["", "## Evaluation", ""]
    if evaluation:
        parts += [
            "Aggregated across this plugin's skills. *Behavioral* is the Tier 2 pass rate with the skill installed;",
            "*baseline* is the same evals run without it.",
            "",
            render_eval_table(evaluation),
            "",
            "Per-query and per-eval detail: [**evaluation report**](evaluation.md).",
        ]
    else:
        parts.append("No evaluation results recorded yet.")
    return "\n".join(parts) + "\n"


def render_skill(p: Plugin, s: Skill, linker: Linker) -> str:
    page = f"docs/plugins/{p.name}/{s.name}/index.md"
    src = f"{s.src.as_posix()}/SKILL.md"
    head = "\n".join(
        [
            '<div class="bw-skillhead">',
            f'<p class="bw-skillhead__desc">{html.escape(s.description)}</p>',
            '<div class="bw-skillhead__meta">',
            f'<a class="bw-tag" href="../">{p.name}</a>',
            f'<a href="{gh(src)}">View <code>SKILL.md</code> on GitHub</a>',
            "</div>",
            "</div>",
            "",
        ]
    )
    body = linker.render(s.body, src, page, self_skill=s.name)
    return (
        front_matter(title=s.name, description=s.description)
        + generated_note(src)
        + "\n"
        + insert_after_h1(body, head).rstrip("\n")
        + "\n"
    )


def render_reference(p: Plugin, s: Skill, linker: Linker) -> str:
    page = f"docs/plugins/{p.name}/{s.name}/reference.md"
    src = f"{s.src.as_posix()}/reference.md"
    meta, body = parse_frontmatter((ROOT / src).read_text())
    title = meta.get("title") or f"{s.name} reference"
    return (
        front_matter(title=title, description=f"Reference companion to the {s.name} skill.")
        + generated_note(src)
        + "\n"
        + linker.render(body, src, page, self_skill=None).rstrip("\n")
        + "\n"
    )


def strip_evolve_note(text: str) -> str:
    return re.sub(r"\A<!--.*?-->\s*", "", text, flags=re.S)


def render_root_evaluation(plugins: list[Plugin]) -> str:
    text = strip_evolve_note((ROOT / "EVALUATION.md").read_text())
    names = {p.name for p in plugins}
    out = []
    for line in text.split("\n"):
        out.append(line)
        m = re.match(r"^## (\S+)$", line)
        if m and m.group(1) in names:
            n = m.group(1)
            out += ["", f"[Plugin page](plugins/{n}/index.md) · [per-eval detail](plugins/{n}/evaluation.md)"]
    return (
        front_matter(title="Evaluation", description="Trigger accuracy and behavioral evals for every plugin, per model.")
        + generated_note("EVALUATION.md (evolve report)")
        + "\n"
        + "\n".join(out).rstrip("\n")
        + "\n"
    )


def render_plugin_evaluation(p: Plugin) -> str:
    src = f"plugins/{p.name}/EVALUATION.md"
    text = strip_evolve_note((ROOT / src).read_text())
    names = {s.name for s in p.skills}
    out = []
    for line in text.split("\n"):
        out.append(line)
        m = re.match(r"^## (\S+)$", line)
        if m and m.group(1) in names:
            out += ["", f"[Skill page]({m.group(1)}/index.md)"]
    return (
        front_matter(title=f"{p.name} evaluation", description=f"Per-query and per-eval results for the {p.name} plugin.")
        + generated_note(f"{src} (evolve report)")
        + "\n"
        + "\n".join(out).rstrip("\n")
        + "\n"
    )


ARROW = (
    '<svg class="bw-card__go" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M7 7h10v10" />'
    '<path d="M7 17 17 7" /></svg>'
)


def render_plugin_cards(plugins: list[Plugin]) -> str:
    out = [
        HTML_LICENSE.rstrip("\n"),
        "{#- Generated by scripts/gen-docs.py from the marketplace + plugin manifests; do not edit by hand.",
        "Regenerate with: make docs-gen. Included by overrides/home.html. -#}",
        '<div class="bw-grid bw-plugins">',
    ]
    for p in plugins:
        n = len(p.skills)
        out += [
            f"    <a class=\"bw-card bw-plugin\" href=\"{{{{ 'plugins/{p.name}/' | url }}}}\">",
            '        <div class="bw-card__top">',
            f'            <span class="bw-card__mark">{p.name}</span>',
            f'            <span class="bw-badge">v{p.version}</span>',
            "        </div>",
            f"        <p>{html.escape(p.description)}</p>",
            '        <div class="bw-card__tags">',
        ]
        out += [f'            <span class="bw-tag">{s.name}</span>' for s in p.skills]
        out += [
            "        </div>",
            '        <div class="bw-plugin__foot">',
            f"            <span>{n} skill{'s' if n != 1 else ''}</span>",
            f"            {ARROW}",
            "        </div>",
            "    </a>",
        ]
    out.append("</div>")
    return "\n".join(out) + "\n"


def eval_stats(plugins: list[Plugin], evaluation: dict) -> dict[str, float | int]:
    cases = 0
    for p in plugins:
        for s in p.skills:
            edir = ROOT / "plugins" / p.name / "evals" / s.name
            for fname, key in (("triggers.json", "triggers"), ("evals.json", "evals")):
                f = edir / fname
                if f.is_file():
                    cases += len(json.loads(f.read_text()).get(key, []))
    models: set[str] = set()
    passed = total = base_passed = base_total = 0
    for pe in evaluation.get("plugins", {}).values():
        models |= set(pe.get("triggers", {})) | set(pe.get("evals", {}))
        for e in pe.get("evals", {}).values():
            base = e.get("baseline")
            # only entries with a baseline, so the comparison is like-for-like
            if not base or not base.get("total") or not e.get("total"):
                continue
            passed += e["passed"]
            total += e["total"]
            base_passed += base["passed"]
            base_total += base["total"]
    return {
        "skills": sum(len(p.skills) for p in plugins),
        "cases": cases,
        "models": len(models),
        "with": passed / total if total else 0.0,
        "without": base_passed / base_total if base_total else 0.0,
    }


def render_eval_stats(stats: dict) -> str:
    def stat(value: str, label: str, extra: str = "") -> list[str]:
        return [
            f'    <div class="bw-stat{extra}">',
            f'        <span class="bw-stat__value">{value}</span>',
            f'        <span class="bw-stat__label">{label}</span>',
            "    </div>",
        ]

    out = [
        HTML_LICENSE.rstrip("\n"),
        "{#- Generated by scripts/gen-docs.py from EVALUATION.json and the eval suites; do not edit by hand.",
        "Regenerate with: make docs-gen. Included by overrides/home.html. -#}",
        '<div class="bw-stats">',
    ]
    out += stat(str(stats["skills"]), "Skills")
    out += stat(f"{stats['cases']:,}", "Eval cases")
    out += stat(str(stats["models"]), "Models evaluated")
    out += [
        '    <div class="bw-stat bw-stat--lift">',
        '        <span class="bw-stat__label">Behavioral pass rate</span>',
        '        <div class="bw-stat__compare">',
        f'            <span class="bw-stat__value">{pct(stats["with"])}</span>',
        '            <span class="bw-stat__vs">with the skill</span>',
        f'            <span class="bw-stat__value bw-stat__value--base">{pct(stats["without"])}</span>',
        '            <span class="bw-stat__vs">without</span>',
        "        </div>",
        '        <div class="bw-stat__bar" role="img" '
        f'aria-label="{pct(stats["with"])} with the skill versus {pct(stats["without"])} without">',
        f'            <span class="bw-stat__fill" style="width: {stats["with"] * 100:.1f}%"></span>',
        f'            <span class="bw-stat__fill bw-stat__fill--base" style="width: {stats["without"] * 100:.1f}%"></span>',
        "        </div>",
        "    </div>",
        "</div>",
    ]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------- driver ----


def generate(plugins: list[Plugin]) -> dict[str, str]:
    """Every owned output, keyed by repo-relative path."""
    evaluation = json.loads((ROOT / "EVALUATION.json").read_text())
    linker = Linker(plugins)
    files: dict[str, str] = {}
    for p in plugins:
        pe = evaluation.get("plugins", {}).get(p.name, {})
        files[f"docs/plugins/{p.name}/index.md"] = render_plugin_index(p, pe, linker)
        if (ROOT / "plugins" / p.name / "EVALUATION.md").is_file():
            files[f"docs/plugins/{p.name}/evaluation.md"] = render_plugin_evaluation(p)
        for s in p.skills:
            files[f"docs/plugins/{p.name}/{s.name}/index.md"] = render_skill(p, s, linker)
            if s.has_reference:
                files[f"docs/plugins/{p.name}/{s.name}/reference.md"] = render_reference(p, s, linker)
    files["docs/evaluation.md"] = render_root_evaluation(plugins)
    files["overrides/partials/plugin-cards.html"] = render_plugin_cards(plugins)
    files["overrides/partials/eval-stats.html"] = render_eval_stats(eval_stats(plugins, evaluation))
    return files


def existing_outputs(base: Path) -> set[str]:
    found = {f for f in OWNED_FILES if (base / f).is_file()}
    for d in OWNED_DIRS:
        found |= {p.relative_to(base).as_posix() for p in (base / d).rglob("*") if p.is_file()}
    return found


def write(base: Path, files: dict[str, str]) -> None:
    for stale in sorted(existing_outputs(base) - set(files)):
        (base / stale).unlink()
    for d in OWNED_DIRS:  # prune directories emptied above
        for p in sorted((base / d).rglob("*"), reverse=True):
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
    for rel, content in files.items():
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.is_file() or dest.read_text() != content:
            dest.write_text(content)


def nav_paths(items: list) -> set[str]:
    paths: set[str] = set()
    for item in items:
        if isinstance(item, str):
            paths.add(item)
        elif isinstance(item, dict):
            for v in item.values():
                paths |= nav_paths(v) if isinstance(v, list) else {v}
    return paths


def nav_snippet(plugins: list[Plugin], files: dict[str, str]) -> str:
    lines = ['  { "Plugins" = [']
    for p in plugins:
        lines.append(f'    {{ "{p.name}" = [')
        lines.append(f'      "plugins/{p.name}/index.md",')
        for s in p.skills:
            idx = f"plugins/{p.name}/{s.name}/index.md"
            if s.has_reference:
                ref = f"plugins/{p.name}/{s.name}/reference.md"
                lines.append(f'      {{ "{s.name}" = ["{idx}", {{ "Reference" = "{ref}" }}] }},')
            else:
                lines.append(f'      {{ "{s.name}" = "{idx}" }},')
        if f"docs/plugins/{p.name}/evaluation.md" in files:
            lines.append(f'      {{ "Evaluation" = "plugins/{p.name}/evaluation.md" }},')
        lines.append("    ] },")
    lines.append("  ] },")
    return "\n".join(lines)


def check_nav(plugins: list[Plugin], files: dict[str, str]) -> list[str]:
    config = tomllib.loads((ROOT / "zensical.toml").read_text())
    nav = nav_paths(config.get("project", {}).get("nav", []))
    pages = {f.removeprefix("docs/") for f in files if f.startswith("docs/")}
    errors = [f"zensical.toml nav is missing generated page: {p}" for p in sorted(pages - nav)]
    errors += [
        f"zensical.toml nav lists a page the generator no longer produces: {p}"
        for p in sorted(n for n in nav if n.startswith("plugins/") and n not in pages)
    ]
    if errors:
        errors.append("expected Plugins section of nav:\n" + nav_snippet(plugins, files))
    return errors


def check(files: dict[str, str]) -> list[str]:
    tmp = Path(tempfile.mkdtemp(prefix="gen-docs.", dir=os.environ.get("TMPDIR")))
    try:
        write(tmp, files)
        errors = []
        current, expected = existing_outputs(ROOT), existing_outputs(tmp)
        errors += [f"missing generated file: {f}" for f in sorted(expected - current)]
        errors += [f"stale generated file (no longer produced): {f}" for f in sorted(current - expected)]
        for rel in sorted(current & expected):
            have, want = (ROOT / rel).read_text(), (tmp / rel).read_text()
            if have != want:
                diff = difflib.unified_diff(
                    have.splitlines(), want.splitlines(), f"a/{rel}", f"b/{rel}", n=1, lineterm=""
                )
                errors.append(f"out of date: {rel}\n" + "\n".join(list(diff)[:20]))
        return errors
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="fail if the committed output is stale")
    args = parser.parse_args()

    plugins = load_plugins()
    files = generate(plugins)
    if args.check:
        errors = check(files)
    else:
        write(ROOT, files)
        errors = []
        print(f"gen-docs: wrote {len(files)} files ({sum(len(p.skills) for p in plugins)} skills)")
    errors += check_nav(plugins, files)
    for e in errors:
        print(f"gen-docs: {e}", file=sys.stderr)
    if errors and args.check:
        print("gen-docs: run `make docs-gen` and commit the result", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
