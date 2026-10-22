"""Run the independently authored overlays against the final graders."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

from harness import config, db
from harness.discover import discover
from harness.evidence import fingerprints
from harness.execute import run_one
from harness.model import RunSpec, Variant
from harness.run_all import git_info
from harness.workspace import safe_path


def load_catalog(path):
    rows = tomllib.loads(Path(path).read_text(encoding="utf-8"))["probe"]
    seen = set()
    for row in rows:
        if set(row) != {"task", "name", "expect", "description"}:
            raise ValueError("invalid catalog fields")
        if not all(isinstance(v, str) and v.strip() for v in row.values()):
            raise ValueError("catalog values must be nonempty strings")
        if row["expect"] not in {"accept", "reject"}:
            raise ValueError("expect must be accept or reject")
        if not all(re.fullmatch(r"[a-z0-9_]+", row[k]) for k in ("task", "name")):
            raise ValueError("unsafe probe identifier")
        key = row["task"], row["name"]
        if key in seen:
            raise ValueError(f"duplicate probe: {key}")
        seen.add(key)
        if not safe_path(Path(path).parent, Path(*key)).is_dir():
            raise ValueError(f"missing overlay: {key}")
    return rows


def overlay_digests(rows, root):
    result = {}
    for row in rows:
        relative = Path(row["task"]) / row["name"]
        digest = hashlib.sha256()
        for path in sorted((root / relative).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                digest.update(path.relative_to(root).as_posix().encode())
                digest.update(path.read_bytes())
        result[relative.as_posix()] = digest.hexdigest()
    return result


def run_probe(item):
    task, row, root = item
    variant = Variant(row["name"], "alt_valid" if row["expect"] == "accept" else "wrong")
    result = run_one(RunSpec(task, variant, "final"), root / row["task"] / row["name"])
    return {**result, "expect": row["expect"], "description": row["description"]}


def table(runs):
    lines = ["task | wrong rejected / total | correct accepted / total"]
    for task in sorted({r["task"] for r in runs}):
        rows = [r for r in runs if r["task"] == task]
        wrong = [r for r in rows if r["expect"] == "reject"]
        correct = [r for r in rows if r["expect"] == "accept"]
        lines.append(f"{task[:2]} | {sum(r['outcome'] == 'FAIL' for r in wrong)}/{len(wrong)} | "
                     f"{sum(r['outcome'] == 'PASS' for r in correct)}/{len(correct)}")
    wrong = [r for r in runs if r["expect"] == "reject"]
    correct = [r for r in runs if r["expect"] == "accept"]
    lines.append(f"TOTAL | {sum(r['outcome'] == 'FAIL' for r in wrong)}/{len(wrong)} | "
                 f"{sum(r['outcome'] == 'PASS' for r in correct)}/{len(correct)}")
    for label, rows, outcome in [("Wrong rejected", wrong, "FAIL"), ("Correct accepted", correct, "PASS")]:
        count = sum(r["outcome"] == outcome for r in rows)
        rate = f"{100 * count / len(rows):.2f}%" if rows else "n/a"
        lines.append(f"{label}: {count}/{len(rows)} ({rate})")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", help="comma-separated task ids or two-digit prefixes, e.g. 01,05 (default: all)")
    parser.add_argument("--jobs", type=int, default=config.JOBS, help="parallel worker processes (default: %(default)s)")
    parser.add_argument("--out", type=Path, default=config.RESULTS, help="results directory (default: results/)")
    parser.add_argument("--baseline", help="path (relative to the repository) of an earlier held-out receipt to "
                                           "record as the pre-hardening baseline; the report shows its catch rate")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("jobs must be positive")
    tasks = discover(selected=args.tasks)
    problem = db.preflight(any("postgres" in t.requires for t in tasks))
    if problem:
        print(f"Preflight failed: {problem}", file=sys.stderr)
        return 2
    by_id = {t.id: t for t in tasks}
    root = config.ROOT / "heldout"
    catalog = root / "catalog.toml"
    all_rows = load_catalog(catalog)
    unknown = {r["task"] for r in all_rows} - {t.id for t in discover()}
    if unknown:
        raise ValueError(f"unknown catalog tasks: {unknown}")
    rows = [r for r in all_rows if r["task"] in by_id]
    if not rows:
        raise ValueError("empty held-out plan")
    task_digests = fingerprints(tasks)
    overlays = overlay_digests(rows, root)
    catalog_digest = hashlib.sha256(catalog.read_bytes()).hexdigest()
    sha, dirty = git_info()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        runs = list(pool.map(run_probe, [(by_id[r["task"]], r, root) for r in rows]))
    changed = (task_digests != fingerprints(tasks) or overlays != overlay_digests(rows, root)
               or catalog_digest != hashlib.sha256(catalog.read_bytes()).hexdigest())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.out / stamp / "heldout.json"
    output.parent.mkdir(parents=True)
    receipt = dict(schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(),
                   git_sha=sha, dirty=dirty, task_digests=task_digests, overlay_digests=overlays,
                   catalog_digest=catalog_digest, source_changed_during_run=changed,
                   invocation=dict(tasks=args.tasks, jobs=args.jobs), baseline_receipt=args.baseline, runs=runs, table=table(runs))
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(receipt["table"])
    print(output)
    for run in runs:
        if run["verdict"] != "ok":
            print(f"{run['task']} / {run['variant']}: {run['verdict']}")
    if changed:
        print("Source changed during execution; rerun against a stable checkout.")
    return int(changed or any(r["verdict"] != "ok" for r in runs))


if __name__ == "__main__":
    raise SystemExit(main())
