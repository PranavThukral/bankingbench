"""Repeat the held-out hardening concurrency tests against reference solutions."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import json

from harness import config
from harness.discover import discover
from harness.evidence import fingerprints
from harness.execute import run_one
from harness.model import RunSpec
from harness.run_all import find_flips


TESTS = {
    "01": "test_concurrent_duplicates_across_app_instances",
    "05": "test_concurrent_reversals_once",
    "08": "test_concurrent_refunds_respect_budget",
}


def measure(item):
    spec, test = item
    return run_one(spec, pytest_args=("-k", test))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=config.JOBS)
    args = parser.parse_args(argv)
    if args.repeat < 1 or args.jobs < 1:
        parser.error("repeat and jobs must be positive")
    tasks = discover(selected=",".join(TESTS))
    before = fingerprints(tasks)
    plan = [(RunSpec(task, next(v for v in task.variants if v.name == "reference"), "final", rep),
             TESTS[task.id[:2]]) for task in tasks for rep in range(args.repeat)]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        runs = list(pool.map(measure, plan))
    flips = find_flips(runs)
    changed = before != fingerprints(tasks)
    summary = []
    for task in tasks:
        rows = [r for r in runs if r["task"] == task.id]
        passed = sum(r["outcome"] == "PASS" and r["tests"]["total"] == 1 for r in rows)
        count = sum(f["task"] == task.id for f in flips)
        summary.append(f"{task.id[:2]} {TESTS[task.id[:2]]}: {passed}/{len(rows)} passed, flips={count}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = config.RESULTS / stamp / "concurrency.json"
    output.parent.mkdir(parents=True)
    receipt = dict(task_digests=before, source_changed_during_run=changed, runs=runs, flips=flips,
                   generated_at=datetime.now(timezone.utc).isoformat(),
                   invocation=dict(repeat=args.repeat, jobs=args.jobs), summary=summary)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("\n".join(summary))
    print(output)
    return int(changed or bool(flips) or any(r["outcome"] != "PASS" or r["tests"]["total"] != 1 for r in runs))


if __name__ == "__main__":
    raise SystemExit(main())
