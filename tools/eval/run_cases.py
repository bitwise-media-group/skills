#!/usr/bin/env python3
# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT

"""Tier 2 behavioral evals, per provider model.

For every plugins/*/evals/<skill>/cases.json, run each case's prompt through a
headless agent session in a throwaway fixture workspace (with the plugin's
skills installed), then grade assertions — deterministic first, LLM-judged last.

Each selected model also gets a token-usage figure per case: the provider's
token-counting API counts the skill's SKILL.md plus the case prompt, priced at
the model's input rate (see tools/eval/providers.py). Executed runs additionally
record the harness-reported usage of the live session — total input tokens
(including cache writes/reads), output tokens, cost, and the wall-clock
seconds of the agent run (grading excluded) — per case, with per-model
totals in the summary.

Runners per provider: Anthropic -> `claude -p`, OpenAI -> `codex exec`.
Google models are token-counted only (no behavioral runner yet). The LLM judge
for `llm` assertions always runs through `claude` regardless of the model under
test, so grading stays comparable across providers.

Case schema:
  {
    "id": "module-scaffold",
    "prompt": "...",
    "files": { "relative/path.tf": "content", ... },        # optional fixture
    "max_turns": 25,                                         # optional
    "assertions": [
      {"type": "file_exists", "path": "modules/x/main.tf"},
      {"type": "file_absent", "path": "modules/x/versions.tf"},
      {"type": "regex", "path": "modules/x/variables.tf", "pattern": "set\\(string\\)"},
      {"type": "not_regex", "pattern": "\\\"this\\\""},      # no path -> final output text
      {"type": "command", "run": "terraform validate", "cwd": "modules/x", "requires": "terraform"},
      {"type": "llm", "text": "The README explains what the module deliberately omits"}
    ]
  }

Usage:
  python3 tools/eval/run_cases.py [--skill NAME] [--case ID] [--models SPEC]
                                  [--timeout SECS] [--jobs N] [--count-only]
                                  [--new]

  --models accepts provider names, model ids, or "all" (comma-separated).
  Default: "anthropic" (all four Anthropic models).
  --jobs caps concurrent cases within each model's batch
  (default: ceil(cpus/2)).
  --new skips skill/model entries whose stored results are already complete —
  a result is incomplete when its timing, input, output, or cost values are
  missing. Skills, models, and cases with no stored result always run.
  Entries whose only gaps are token counts the counting API cannot produce
  (unsupported model, missing credential) are also skipped — rerunning could
  never fill them.

Results merge into evals-results/cases-<skill>.json (one entry per model,
persisted as each model finishes), then tools/eval/report.py regenerates
EVALUATION.md and plugins/*/EVALUATION.md.
"""

import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import providers
import report

REPO = providers.REPO
RESULTS_DIR = providers.RESULTS_DIR
DEFAULT_TOOLS = "Read Write Edit Glob Grep Skill Bash(terraform *) Bash(tflint *) Bash(mkdir *)"
JUDGE_PROMPT = """You are grading an AI coding agent's work. Assertion to verify:

{assertion}

The agent's final response was:
---
{output}
---

Files in the agent's workspace are at: {workspace}
Reply with ONLY a JSON object: {{"passed": true|false, "evidence": "<short quote or file fact supporting the verdict>"}}"""


def eval_sets(skill_filter):
    for cases in sorted(REPO.glob("plugins/*/evals/*/cases.json")):
        skill = cases.parent.name
        plugin_dir = cases.parents[2]
        if skill_filter and skill != skill_filter:
            continue
        yield plugin_dir, skill, json.loads(cases.read_text())


def skip_reason(entry, cases, model, execute, probe_count):
    """Why --new may skip this skill/model, or None when a (re)run is needed.
    A rerun is needed when any current case has no stored result, or a
    stored result is missing its timing (run_seconds), input (input_tokens,
    measured input), output (passed, measured output tokens), or cost
    (est_input_cost_usd, measured cost) values. Fields a run could never
    fill are exempt: costs for models without published pricing, the
    execution fields when this invocation is count-only, and the token-count
    fields when probe_count(case) shows the counting API cannot count for
    this model (unsupported model, missing credential) — rerunning would
    leave them missing anyway."""
    stored = {r.get("id"): r for r in (entry or {}).get("results") or []}
    priced = model["input"] is not None and model["output"] is not None
    uncounted = None
    for case in cases:
        result = stored.get(case["id"])
        if result is None:
            return None
        if execute:
            measured = result.get("measured") or {}
            run_fields = [result.get("passed"), result.get("run_seconds"),
                          measured.get("input_tokens"), measured.get("output_tokens")]
            if priced:
                run_fields.append(measured.get("cost_usd"))
            if any(value is None for value in run_fields):
                return None
        counted = [result.get("input_tokens")]
        if model["input"] is not None:
            counted.append(result.get("est_input_cost_usd"))
        if uncounted is None and any(value is None for value in counted):
            uncounted = case
    if uncounted is None:
        return "results complete"
    return None if probe_count(uncounted) else "token counts unavailable"


def make_workspace(plugin_dir, files):
    ws = Path(tempfile.mkdtemp(prefix="cases.", dir=os.environ.get("TMPDIR")))
    for skills_dir in (ws / ".claude" / "skills", ws / ".agents" / "skills"):
        skills_dir.mkdir(parents=True)
        for sk in sorted((plugin_dir / "skills").iterdir()):
            if (sk / "SKILL.md").is_file():
                (skills_dir / sk.name).symlink_to(sk)
    for rel, content in (files or {}).items():
        path = ws / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return ws


def _run_cli(cmd, ws, timeout):
    """Run an agent CLI and return its stdout. A timed-out run returns the
    partial stdout (so the case fails its assertions and the eval moves on)
    instead of raising TimeoutExpired and aborting the whole run."""
    try:
        proc = subprocess.run(
            cmd, cwd=ws, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, errors="replace", timeout=timeout,
        )
        return proc.stdout
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):  # TimeoutExpired carries bytes even in text mode
            out = out.decode(errors="replace")
        print(f"  warn: {cmd[0]} timed out after {timeout}s; grading partial output",
              file=sys.stderr)
        return out


def run_agent_claude(ws, case, model, timeout):
    """Returns (final_output, usage|None). Usage is the CLI-reported token usage."""
    cmd = [
        "claude", "-p", case["prompt"],
        "--model", model,
        "--output-format", "json",
        "--max-turns", str(case.get("max_turns", 25)),
        "--allowedTools", case.get("allowed_tools", DEFAULT_TOOLS),
    ]
    stdout = _run_cli(cmd, ws, timeout)
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout, None
    usage = payload.get("usage") or {}
    measured = {
        # Cache writes/reads are input tokens too; fold them in so the figure
        # reflects everything the session consumed (cost_usd already does).
        "input_tokens": (usage.get("input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0),
        "output_tokens": usage.get("output_tokens"),
        "cost_usd": payload.get("total_cost_usd"),
    } if usage else None
    return payload.get("result", ""), measured


def run_agent_codex(ws, case, model, timeout):
    """Best-effort codex exec run: concatenates agent messages, captures usage."""
    cmd = [
        "codex", "exec", case["prompt"],
        "--json", "--skip-git-repo-check",
        "--sandbox", "workspace-write",
        "-m", model,
    ]
    stdout = _run_cli(cmd, ws, timeout)
    texts, usage = [], None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            texts.append(item.get("text", ""))
        if event.get("type") == "turn.completed" and event.get("usage"):
            usage = {
                "input_tokens": event["usage"].get("input_tokens"),
                "output_tokens": event["usage"].get("output_tokens"),
                "cost_usd": None,
            }
    return "\n".join(texts) if texts else stdout, usage


CASE_RUNNERS = {
    "anthropic": run_agent_claude,
    "openai": run_agent_codex,
}


def grade(assertion, ws, output, timeout):
    """Returns (passed: bool|None, evidence: str). None = skipped."""
    kind = assertion["type"]

    if kind in ("file_exists", "file_absent"):
        exists = (ws / assertion["path"]).exists()
        passed = exists if kind == "file_exists" else not exists
        return passed, f"{assertion['path']} {'exists' if exists else 'missing'}"

    if kind in ("regex", "not_regex"):
        if "path" in assertion:
            target = ws / assertion["path"]
            if not target.is_file():
                return False, f"{assertion['path']} missing"
            text = target.read_text(errors="replace")
        else:
            text = output
        match = re.search(assertion["pattern"], text, re.MULTILINE)
        passed = bool(match) if kind == "regex" else not match
        evidence = match.group(0)[:120] if match else "no match"
        return passed, evidence

    if kind == "command":
        binary = assertion.get("requires")
        if binary and not shutil.which(binary):
            return None, f"skipped: {binary} not installed"
        cwd = ws / assertion.get("cwd", ".")
        proc = subprocess.run(
            assertion["run"], shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout,
        )
        expected = assertion.get("expect_exit", 0)
        tail = (proc.stdout + proc.stderr).strip()[-200:]
        return proc.returncode == expected, f"exit {proc.returncode}: {tail}"

    if kind == "llm":
        prompt = JUDGE_PROMPT.format(
            assertion=assertion["text"], output=output[:8000], workspace=ws,
        )
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json", "--max-turns", "4",
                 "--allowedTools", "Read Glob Grep"],
                capture_output=True, text=True, errors="replace", timeout=timeout,
            )
            result = json.loads(proc.stdout).get("result", "")
            verdict = json.loads(re.search(r"\{.*\}", result, re.DOTALL).group(0))
            return bool(verdict.get("passed")), str(verdict.get("evidence", ""))[:200]
        except Exception as exc:  # judge timeout or unparseable output -> fail loudly
            return False, f"judge error: {exc}"

    return False, f"unknown assertion type: {kind}"


def run_case(plugin_dir, skill, case, provider_key, model, args):
    runner = CASE_RUNNERS[provider_key]
    ws = make_workspace(plugin_dir, case.get("files"))
    try:
        start = time.monotonic()
        output, measured = runner(ws, case, model["id"], args.timeout)
        # Agent run only — grading (and the claude-backed LLM judge) would
        # pollute the model-speed signal.
        run_seconds = round(time.monotonic() - start, 1)
        graded, lines = [], []
        for assertion in case["assertions"]:
            passed, evidence = grade(assertion, ws, output, args.timeout)
            graded.append({**assertion, "passed": passed, "evidence": evidence})
            marker = "SKIP" if passed is None else ("PASS" if passed else "FAIL")
            label = assertion.get("text") or assertion.get("pattern") \
                or assertion.get("run") or assertion.get("path")
            lines.append(f"  [{marker}] {case['id']}: {label}")
        # One write per case so concurrently-running cases don't interleave.
        print("\n".join(lines), flush=True)
        case_passed = all(g["passed"] is not False for g in graded)
        if measured:
            measured["cost_usd"] = measured.get("cost_usd") \
                or providers.usage_cost_usd(model, measured)
        return case_passed, graded, measured, run_seconds
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill", help="only run evals for this skill")
    ap.add_argument("--case", help="only run the case with this id")
    ap.add_argument("--models", default="anthropic",
                    help='comma-separated provider names / model ids, or "all"')
    ap.add_argument("--timeout", type=int, default=600, help="seconds per agent run")
    ap.add_argument("--jobs", type=int, default=providers.default_jobs(),
                    help="concurrent cases (default: ceil(cpus/2))")
    ap.add_argument("--count-only", action="store_true",
                    help="skip agent runs; only compute token usage per model")
    ap.add_argument("--new", action="store_true",
                    help="only run evals whose stored results are missing "
                         "timing, input, output, or cost values a rerun could fill")
    args = ap.parse_args()

    if not args.count_only:
        print(f"parallelism: {args.jobs} concurrent cases")
    selected = providers.select_models(args.models)
    counter = providers.TokenCounter()
    RESULTS_DIR.mkdir(exist_ok=True)
    any_failed = False

    for plugin_dir, skill, cases in eval_sets(args.skill):
        cases = [c for c in cases if not args.case or c["id"] == args.case]
        if not cases:
            continue
        out = RESULTS_DIR / f"cases-{skill}.json"
        data = providers.load_results(out, plugin_dir.name, skill)
        skill_md = (plugin_dir / "skills" / skill / "SKILL.md").read_text()

        for provider_key, model in selected:
            runner_available = provider_key in CASE_RUNNERS \
                and shutil.which(providers.PROVIDERS[provider_key]["runner"]) is not None
            execute = runner_available and not args.count_only
            if args.new:
                reason = skip_reason(
                    data["models"].get(model["id"]), cases, model, execute,
                    lambda case: counter.count(
                        provider_key, model["id"], f"{skill_md}\n\n{case['prompt']}",
                    ) is not None,
                )
                if reason:
                    print(f"\n=== {skill} / {model['id']} (skip: {reason}) ===")
                    continue
            if not execute and not args.count_only:
                print(f"  warn: no behavioral runner for {model['id']}; "
                      f"token counts only", file=sys.stderr)

            mode = "run" if execute else "count-only"
            print(f"\n=== {skill} / {model['id']} ({mode}) ===")
            # Token counting stays in this thread (TokenCounter is not
            # thread-safe and cache-cheap); only case runs go parallel — each
            # gets its own workspace inside run_case.
            results = []
            for case in cases:
                tokens = counter.count(
                    provider_key, model["id"], f"{skill_md}\n\n{case['prompt']}",
                )
                results.append({
                    "id": case["id"],
                    "passed": None,
                    "assertions": None,
                    "run_seconds": None,
                    "input_tokens": tokens,
                    "est_input_cost_usd": providers.input_cost_usd(model, tokens),
                    "measured": None,
                })
            if execute:
                with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                    futures = {
                        pool.submit(run_case, plugin_dir, skill, case,
                                    provider_key, model, args): i
                        for i, case in enumerate(cases)
                    }
                    for future in as_completed(futures):
                        passed, graded, measured, run_seconds = future.result()
                        any_failed |= not passed
                        results[futures[future]].update(
                            {"passed": passed, "assertions": graded,
                             "measured": measured, "run_seconds": run_seconds})

            executed = [r for r in results if r["passed"] is not None]
            token_counts = [r["input_tokens"] for r in results if r["input_tokens"] is not None]
            costs = [r["est_input_cost_usd"] for r in results if r["est_input_cost_usd"] is not None]
            run_times = [r["run_seconds"] for r in executed if r["run_seconds"] is not None]
            usages = [r["measured"] for r in results if r["measured"]]
            measured_in = [u["input_tokens"] for u in usages if u.get("input_tokens") is not None]
            measured_out = [u["output_tokens"] for u in usages if u.get("output_tokens") is not None]
            measured_costs = [u["cost_usd"] for u in usages if u.get("cost_usd") is not None]
            data["models"][model["id"]] = {
                "provider": provider_key,
                "display": model["display"],
                "executed": bool(executed),
                "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "results": results,
                "summary": {
                    "passed": sum(r["passed"] for r in executed) if executed else None,
                    "total": len(results),
                    "avg_run_seconds": round(sum(run_times) / len(run_times), 1) if run_times else None,
                    "input_tokens": sum(token_counts) if token_counts else None,
                    "est_input_cost_usd": round(sum(costs), 6) if costs else None,
                    "measured_input_tokens": sum(measured_in) if measured_in else None,
                    "measured_output_tokens": sum(measured_out) if measured_out else None,
                    "measured_cost_usd": round(sum(measured_costs), 6) if measured_costs else None,
                },
            }
            if executed:
                avg = f", avg run {sum(run_times) / len(run_times):.1f}s" if run_times else ""
                print(f"  {sum(r['passed'] for r in executed)}/{len(results)} cases passed{avg}")
            # Persist after every model so an interrupted sweep keeps the
            # models that already finished.
            out.write_text(json.dumps(data, indent=2) + "\n")
            print(f"  -> {out.relative_to(REPO)}")

    counter.save()
    report.generate()
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
