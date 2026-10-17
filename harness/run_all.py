import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import time

from harness import config, db
from harness.discover import discover
from harness.execute import run_one
from harness.evidence import fingerprints
from harness.model import RunSpec


def git_info():
    def git(*args):
        history = config.ROOT / ".audit-history"
        command = ["git"]
        if history.exists():
            command += [f"--git-dir={history}", f"--work-tree={config.ROOT}"]
        return subprocess.check_output([*command, *args], cwd=config.ROOT, text=True).strip()
    try:
        return git("rev-parse", "--short", "HEAD"), bool(git("status", "--porcelain"))
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True


def find_flips(runs):
    groups = {}
    for run in runs:
        key = (run["task"], run["variant"], run["grader"])
        groups.setdefault(key, set()).add((run["outcome"], run["verdict"], tuple(run["failed_tests"])))
    return [dict(task=k[0], variant=k[1], grader=k[2]) for k, v in groups.items() if len(v) > 1]


def summary(matrix):
    rows = matrix["runs"]
    final = [r for r in rows if r["grader"] == "final"]
    naive = [r for r in rows if r["grader"] == "naive"]
    return (f"runs={len(rows)} final_ok={sum(r['verdict'] == 'ok' for r in final)}/{len(final)} "
            f"naive_false_pass={sum(r['verdict'] == 'false_pass' for r in naive)} "
            f"infra_errors={sum(r['verdict'] == 'infra_error' for r in rows)} "
            f"flips={len(matrix['flips'])} wall_s={matrix.get('wall_s', 0):.3f}")


def latest(base=config.RESULTS):
    base = Path(base)
    pointer = (base / "LATEST").read_text(encoding="utf-8").strip()
    path = base / pointer / "matrix.json"
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("unsafe LATEST pointer")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks")
    parser.add_argument("--variants")
    parser.add_argument("--grader", choices=["naive", "final", "all"], default="final")
    parser.add_argument("--jobs", type=int, default=config.JOBS)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--out", type=Path, default=config.RESULTS)
    parser.add_argument("--keep-workspaces", action="store_true")
    args = parser.parse_args(argv)
    if args.jobs < 1 or args.repeat < 1:
        parser.error("jobs and repeat must be positive")
    start = time.perf_counter()
    try:
        tasks = discover(selected=args.tasks)
        versions = ["naive", "final"] if args.grader == "all" else [args.grader]
        specs = [RunSpec(t, v, g, rep, args.keep_workspaces)
                 for t in tasks for v in t.variants for g in versions
                 if (t.path / "grader" / g).is_dir()
                 if not args.variants or v.name in args.variants.split(",")
                 for rep in range(args.repeat)]
        if not specs:
            raise ValueError("empty run plan")
        sha, dirty = git_info()
        source_digests = fingerprints(tasks)
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            runs = list(pool.map(run_one, specs))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = args.out / stamp
        output.mkdir(parents=True)
        matrix = dict(schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(),
                      git_sha=sha, dirty=dirty, status="private draft",
                      env=dict(python=platform.python_version(), postgres=db.version(),
                               hypothesis_profile="ci", platform=platform.platform()),
                      runs=runs, flips=find_flips(runs), wall_s=round(time.perf_counter() - start, 3),
                      task_digests=source_digests,
                      source_changed_during_run=(source_digests != fingerprints(tasks)),
                      invocation=dict(tasks=args.tasks, variants=args.variants, grader=args.grader,
                                      repeat=args.repeat, jobs=args.jobs))
        (output / "matrix.json").write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
        (args.out / "LATEST").write_text(stamp + "\n", encoding="utf-8")
        print(summary(matrix))
        print(output / "matrix.json")
        for r in runs:
            if r["grader"] == "final" and r["verdict"] != "ok":
                print(f"{r['task']} {r['variant']}: {r['verdict']}\n{r['stderr_tail']}")
        if matrix["source_changed_during_run"]:
            print("Source changed during execution; rerun against a stable checkout.")
            return 2
        return int(bool(matrix["flips"]) or any(r["verdict"] != "ok" for r in runs if r["grader"] == "final"))
    except Exception as exc:
        print(f"Harness error: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
