#!/usr/bin/env python3
# Copyright 2026 Bitwise Media Group
# SPDX-License-Identifier: MIT

"""Tier 1 trigger-accuracy evals, per provider model.

For every plugins/*/evals/<skill>/triggers.json, run each query through a headless
agent session in a throwaway workspace where the plugin's skills are installed,
and check whether the skill under test activates. A query passes when its observed
trigger rate agrees with `should_trigger` (threshold 0.5).

Each selected model also gets a token-usage figure per query: the provider's
token-counting API is asked to count the skill's SKILL.md plus the query — the
marginal context a triggering eval loads — and the count is priced at the model's
input rate (see tools/eval/providers.py). Executed queries also record the
average wall-clock seconds per run, since model speed varies widely.

Runners per provider: Anthropic -> `claude -p`, OpenAI -> `codex exec`,
Google -> `gemini -p`. Models whose runner CLI is missing are token-counted only.

Usage:
  python3 tools/eval/run_triggers.py [--skill NAME] [--models SPEC] [--runs N]
                                     [--timeout SECS] [--jobs N] [--count-only]

  --models accepts provider names, model ids, or "all" (comma-separated).
  Default: "anthropic" (all four Anthropic models).
  --jobs caps concurrent agent runs within each model's batch
  (default: ceil(cpus/2)).

Results merge into evals-results/triggers-<skill>.json (one entry per model,
persisted as each model finishes), then tools/eval/report.py regenerates
EVALUATION.md and plugins/*/EVALUATION.md.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import providers
import report

REPO = providers.REPO
RESULTS_DIR = providers.RESULTS_DIR


def eval_sets(skill_filter):
    for triggers in sorted(REPO.glob("plugins/*/evals/*/triggers.json")):
        skill = triggers.parent.name
        plugin_dir = triggers.parents[2]
        if skill_filter and skill != skill_filter:
            continue
        yield plugin_dir, skill, json.loads(triggers.read_text())


def make_workspace(plugin_dir):
    """Throwaway project dir with ALL of the plugin's skills installed (so the
    skill under test has to win against its siblings), linked everywhere the
    supported runners look: .claude/skills, .agents/skills, .gemini/skills."""
    ws = Path(tempfile.mkdtemp(prefix="triggers.", dir=os.environ.get("TMPDIR")))
    for skills_dir in (ws / ".claude" / "skills", ws / ".agents" / "skills", ws / ".gemini" / "skills"):
        skills_dir.mkdir(parents=True)
        for sk in sorted((plugin_dir / "skills").iterdir()):
            if (sk / "SKILL.md").is_file():
                (skills_dir / sk.name).symlink_to(sk)
    return ws


def _scan_jsonl(proc, deadline, line_hit, stderr_log=None):
    """Scan proc's stdout for a line_hit match until EOF or the deadline.

    The deadline is enforced by a watchdog that kills the process: a per-line
    clock check never fires while the runner is silent (rate-limit backoff,
    stalled request), because readline blocks until a line arrives."""
    timed_out = threading.Event()

    def expire():
        timed_out.set()
        proc.kill()

    watchdog = threading.Timer(max(0.0, deadline - time.monotonic()), expire)
    watchdog.start()
    try:
        for line in proc.stdout:
            if line_hit(line):
                return True
        return False
    finally:
        watchdog.cancel()
        proc.kill()
        proc.wait()
        if timed_out.is_set():
            detail = ""
            if stderr_log is not None:
                stderr_log.seek(0)
                tail = stderr_log.read().strip()[-300:]
                if tail:
                    detail = f"; stderr tail: {tail}"
            print(f"  warn: runner timed out; counted as no-trigger{detail}",
                  file=sys.stderr)


def triggered_claude(ws, query, skill, model, timeout):
    """True if a Skill/Read tool_use in the session targets `skill`."""
    cmd = [
        "claude", "-p", query,
        "--model", model,
        "--output-format", "stream-json", "--verbose",
        "--max-turns", "2",
        "--allowedTools", "Skill Read",
    ]
    proc = subprocess.Popen(
        cmd, cwd=ws, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, errors="replace",
    )

    def hit(line):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return False
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") != "tool_use":
                continue
            payload = json.dumps(block.get("input") or {})
            if block.get("name") == "Skill" and skill in payload:
                return True
            if block.get("name") == "Read" and f"skills/{skill}/SKILL.md" in payload:
                return True
        return False

    return _scan_jsonl(proc, time.monotonic() + timeout, hit)


def triggered_codex(ws, query, skill, model, timeout):
    """Best-effort: codex exec event stream mentions the skill's SKILL.md path."""
    cmd = ["codex", "exec", query, "--json", "--skip-git-repo-check", "-m", model]
    # Spool stderr to a file (not a pipe nobody drains) so a timed-out run can
    # report what codex was complaining about — rate limits, auth, model errors.
    with tempfile.TemporaryFile(
        mode="w+", errors="replace", dir=os.environ.get("TMPDIR"),
    ) as stderr_log:
        proc = subprocess.Popen(
            cmd, cwd=ws, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=stderr_log, text=True, errors="replace",
        )
        needle = f"skills/{skill}/SKILL.md"
        return _scan_jsonl(proc, time.monotonic() + timeout,
                           lambda line: needle in line, stderr_log=stderr_log)


def triggered_gemini(ws, query, skill, model, timeout):
    """Best-effort: gemini CLI output mentions the skill's SKILL.md path."""
    cmd = ["gemini", "-p", query, "-m", model, "--output-format", "json"]
    proc = subprocess.Popen(
        cmd, cwd=ws, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, errors="replace",
    )
    needle = f"skills/{skill}/SKILL.md"
    return _scan_jsonl(proc, time.monotonic() + timeout, lambda line: needle in line)


TRIGGER_RUNNERS = {
    "anthropic": triggered_claude,
    "openai": triggered_codex,
    "google": triggered_gemini,
}


def run_queries(runner, ws, skill, model_id, cases, results, args):
    """Execute every query's runs concurrently (--jobs at a time), fill each
    result's trigger_rate/passed/avg_run_seconds in place, and print verdicts
    as queries finish. Sharing the workspace is safe: trigger sessions are
    read-only. Returns True when any query failed."""
    def timed(query):
        start = time.monotonic()
        hit = runner(ws, query, skill, model_id, args.timeout)
        return hit, time.monotonic() - start

    hits = [0] * len(cases)
    elapsed = [0.0] * len(cases)
    remaining = [args.runs] * len(cases)
    failed = False
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(timed, case["query"]): i
            for i, case in enumerate(cases)
            for _ in range(args.runs)
        }
        for future in as_completed(futures):
            i = futures[future]
            hit, seconds = future.result()
            hits[i] += bool(hit)
            elapsed[i] += seconds
            remaining[i] -= 1
            if remaining[i]:
                continue
            rate = hits[i] / args.runs
            avg = elapsed[i] / args.runs
            expected = cases[i]["should_trigger"]
            passed = (rate >= 0.5) if expected else (rate < 0.5)
            failed |= not passed
            results[i].update({"trigger_rate": rate, "passed": passed,
                               "avg_run_seconds": round(avg, 1)})
            marker = "PASS" if passed else "FAIL"
            print(f"  [{marker}] rate={rate:.2f} avg={avg:.1f}s "
                  f"expect={'+' if expected else '-'} {cases[i]['query'][:70]}")
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill", help="only run evals for this skill")
    ap.add_argument("--models", default="anthropic",
                    help='comma-separated provider names / model ids, or "all"')
    ap.add_argument("--runs", type=int, default=3, help="runs per query (default 3)")
    ap.add_argument("--timeout", type=int, default=120, help="seconds per run")
    ap.add_argument("--jobs", type=int, default=providers.default_jobs(),
                    help="concurrent agent runs (default: ceil(cpus/2))")
    ap.add_argument("--count-only", action="store_true",
                    help="skip agent runs; only compute token usage per model")
    args = ap.parse_args()

    if not args.count_only:
        print(f"parallelism: {args.jobs} concurrent agent runs")
    selected = providers.select_models(args.models)
    counter = providers.TokenCounter()
    RESULTS_DIR.mkdir(exist_ok=True)
    any_failed = False

    for plugin_dir, skill, cases in eval_sets(args.skill):
        out = RESULTS_DIR / f"triggers-{skill}.json"
        data = providers.load_results(out, plugin_dir.name, skill)
        skill_md = (plugin_dir / "skills" / skill / "SKILL.md").read_text()
        ws = make_workspace(plugin_dir)
        try:
            for provider_key, model in selected:
                runner = TRIGGER_RUNNERS[provider_key]
                binary = providers.PROVIDERS[provider_key]["runner"]
                execute = not args.count_only and shutil.which(binary) is not None
                if not execute and not args.count_only:
                    print(f"  warn: `{binary}` CLI not found; "
                          f"{model['id']} gets token counts only", file=sys.stderr)

                mode = "run" if execute else "count-only"
                print(f"\n=== {skill} / {model['id']} "
                      f"({len(cases)} queries x {args.runs} runs, {mode}) ===")
                # Token counting stays in this thread (TokenCounter is not
                # thread-safe and cache-cheap); only agent runs go parallel.
                results = []
                for case in cases:
                    tokens = counter.count(
                        provider_key, model["id"], f"{skill_md}\n\n{case['query']}",
                    )
                    results.append({
                        "query": case["query"],
                        "should_trigger": case["should_trigger"],
                        "trigger_rate": None,
                        "passed": None,
                        "avg_run_seconds": None,
                        "input_tokens": tokens,
                        "est_input_cost_usd": providers.input_cost_usd(model, tokens),
                    })
                if execute:
                    any_failed |= run_queries(
                        runner, ws, skill, model["id"], cases, results, args,
                    )

                executed = [r for r in results if r["passed"] is not None]
                token_counts = [r["input_tokens"] for r in results if r["input_tokens"] is not None]
                costs = [r["est_input_cost_usd"] for r in results if r["est_input_cost_usd"] is not None]
                run_times = [r["avg_run_seconds"] for r in executed if r["avg_run_seconds"] is not None]
                data["models"][model["id"]] = {
                    "provider": provider_key,
                    "display": model["display"],
                    "executed": bool(executed),
                    "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "runs_per_query": args.runs if executed else None,
                    "results": results,
                    "summary": {
                        "passed": sum(r["passed"] for r in executed) if executed else None,
                        "total": len(results),
                        "avg_run_seconds": round(sum(run_times) / len(run_times), 1) if run_times else None,
                        "input_tokens": sum(token_counts) if token_counts else None,
                        "est_input_cost_usd": round(sum(costs), 6) if costs else None,
                    },
                }
                if executed:
                    avg = f", avg run {sum(run_times) / len(run_times):.1f}s" if run_times else ""
                    print(f"  {sum(r['passed'] for r in executed)}/{len(results)} queries passed{avg}")
                # Persist after every model so an interrupted sweep keeps the
                # models that already finished.
                out.write_text(json.dumps(data, indent=2) + "\n")
                print(f"  -> {out.relative_to(REPO)}")
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    counter.save()
    report.generate()
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
