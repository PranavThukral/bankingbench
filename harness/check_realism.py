import argparse
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from harness import config, db
from harness.discover import discover
from harness.evidence import fingerprints
from harness.execute import run_one
from harness.model import RunSpec, Variant
from harness.verdict import hits
from harness.workspace import materialize

# Minimum changed lines (added + removed) between starter and reference over .py files.
# A starter that is the reference minus one line turns the ticket into "find the bug".
DIFF_FLOORS = {"hard": 40, "medium": 25, "easy": 12}


LINT_PATHS = ("harness", "graderlib", "tasks", "tools")


def lint_py312(root=config.ROOT):
    """Lint the whole pack against the Python 3.12 language level used by the runner image."""
    command = [sys.executable, "-m", "ruff", "check", "--target-version", "py312", "--no-cache",
               *[p for p in LINT_PATHS if (Path(root) / p).exists()]]
    proc = subprocess.run(command, cwd=root, capture_output=True, text=True)
    return dict(ok=proc.returncode == 0, output=(proc.stdout + proc.stderr).strip()[-2000:])


def _py_files(root):
    return {p.relative_to(root).as_posix() for p in Path(root).rglob("*.py") if "__pycache__" not in p.parts}


def _lines(root, relative):
    path = Path(root) / relative
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def ref_diff_lines(task):
    """Changed lines (added + removed) from starter/ to solutions/reference/ over .py files."""
    starter, reference = task.path / "starter", task.path / "solutions" / "reference"
    deleted = set()
    marker = reference / "__delete__.txt"
    if marker.exists():
        deleted = {line.strip().replace("\\", "/") for line in marker.read_text(encoding="utf-8").splitlines()
                   if line.strip().endswith(".py")}
    total = 0
    for relative in sorted(_py_files(reference) | deleted):
        before = _lines(starter, relative)
        after = [] if relative in deleted else _lines(reference, relative)
        total += sum(line[:1] in "+-" and not line.startswith(("+++", "---"))
                     for line in difflib.unified_diff(before, after, n=0, lineterm=""))
    return total


def diff_floor(task):
    return DIFF_FLOORS[task.difficulty]


def regressive_wrong(variant, starter_failed_tests):
    """The variant's must_fail tests that the unmodified starter passes under the final grader.

    A non-empty result means the wrong variant breaks behaviour the starter already got right,
    so it is a regression rather than a plausible incomplete solution.
    """
    caught = set(hits(variant.must_fail, starter_failed_tests))
    return [test for test in variant.must_fail if test not in caught]


def rationale_logged(task, variant):
    notes = task.path / "NOTES.md"
    if not notes.is_file() or not variant.regression_rationale:
        return False
    text = " ".join(notes.read_text(encoding="utf-8").split())
    return variant.name in text and " ".join(variant.regression_rationale.split()) in text


def design_rows(tasks, starter_failed=None):
    """Design-level realism: diff floors and regression rationales. Returns one row per task."""
    rows = []
    for task in tasks:
        changed, floor = ref_diff_lines(task), diff_floor(task)
        if starter_failed is None:
            result = run_one(RunSpec(task, Variant("starter", "starter"), "final"))
            if result["outcome"] == "ERROR":
                raise RuntimeError(f"{task.id}: starter final run errored: {result['stderr_tail']}")
            failed = result["failed_tests"]
        else:
            failed = starter_failed[task.id]
        regressive = {}
        for variant in task.variants:
            if variant.kind != "wrong":
                continue
            tests = regressive_wrong(variant, failed)
            ok = (not tests and not variant.regression_rationale) or (
                bool(tests) and rationale_logged(task, variant))
            regressive[variant.name] = dict(tests=tests, rationale=variant.regression_rationale,
                                            ok=ok)
        rows.append(dict(task=task.id, difficulty=task.difficulty, ref_diff_lines=changed, floor=floor,
                         diff_ok=changed >= floor, regressive=regressive,
                         ok=changed >= floor and all(v["ok"] for v in regressive.values())))
    return rows


def check(tasks):
    rows = []
    config.TMP.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        for variant in task.variants:
            with tempfile.TemporaryDirectory(dir=config.TMP) as directory:
                base = Path(directory)
                work = materialize(task.path / "starter", None if variant.name == "starter" else
                                   task.path / "solutions" / variant.name, base / "work")
                env = {**os.environ, **config.DETERMINISM, "PYTHONPATH": str(work)}
                name = db.db_name(base.name)
                created = False
                try:
                    if "postgres" in task.requires:
                        env["DATABASE_URL"] = db.create_db(name)
                        created = True
                    commands = [[sys.executable, "-m", "compileall", "-q", str(work)],
                                [sys.executable, "-m", "ruff", "check", "--select", "F,E9", str(work)],
                                [sys.executable, "-m", "pytest", str(work / "tests"), "-q",
                                 f"--rootdir={work}", f"--confcutdir={work}",
                                 f"--basetemp={base / 'pytest-tmp'}", "-p", "no:cacheprovider"]]
                    outputs = [subprocess.run(cmd, cwd=work, env=env, capture_output=True,
                                              text=True, timeout=task.timeout_seconds) for cmd in commands]
                    codes = [p.returncode for p in outputs]
                    passed = codes[:2] == [0, 0] and codes[2] == (1 if variant.name == "starter" else 0)
                    row = dict(task=task.id, variant=variant.name, ok=passed, codes=codes)
                    if not passed:
                        row["detail"] = "\n".join(p.stdout + p.stderr for p in outputs)
                except Exception as exc:
                    row = dict(task=task.id, variant=variant.name, ok=False, detail=str(exc))
                finally:
                    if created:
                        db.drop_db(name)
                rows.append(row)
                print(f"{task.id} {variant.name}: {'PASS' if row['ok'] else 'FAIL'}", flush=True)
                if not row["ok"]:
                    print(row.get("detail", ""), flush=True)
    return rows


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--tasks")
    args = p.parse_args(argv)
    tasks = discover(selected=args.tasks)
    rows = check(tasks)
    design = design_rows(tasks)
    print("\nTask | difficulty | ref_diff_lines | floor | regressive wrong variants")
    for row in design:
        flagged = {k: v["tests"] for k, v in row["regressive"].items() if v["tests"]}
        verdict = "ok" if row["ok"] else "FAIL"
        print(f"{row['task']} | {row['difficulty']} | {row['ref_diff_lines']} | >= {row['floor']} | "
              f"{flagged or 'none'} | {verdict}", flush=True)
        for name, info in row["regressive"].items():
            if not info["ok"]:
                print(f"  {name}: regressive tests {info['tests']} without a logged regression_rationale"
                      if info["tests"] else f"  {name}: regression_rationale present but variant is not regressive")
    lint = lint_py312()
    print(f"\nruff check --target-version py312 {' '.join(LINT_PATHS)}: {'PASS' if lint['ok'] else 'FAIL'}", flush=True)
    if not lint["ok"]:
        print(lint["output"], flush=True)
    config.RESULTS.mkdir(exist_ok=True)
    receipt = dict(task_digests=fingerprints(tasks), rows=rows, design=design, py312_lint=lint)
    (config.RESULTS / "realism.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return int(not rows or any(not r["ok"] for r in rows) or any(not d["ok"] for d in design)
               or not lint["ok"])


if __name__ == "__main__":
    raise SystemExit(main())
