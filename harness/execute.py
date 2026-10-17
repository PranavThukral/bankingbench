from dataclasses import asdict
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from harness import config, db, junit, verdict, workspace
from harness.model import RunResult


def run_one(spec):
    started = time.perf_counter()
    task, variant = spec.task, spec.variant
    run_id = f"{task.id}__{variant.name}__{spec.grader}__r{spec.repeat}__{uuid.uuid4().hex[:8]}"
    config.TMP.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run_", dir=config.TMP))
    name, database_created = db.db_name(run_id), False
    outcome, counts, failures, tail = "ERROR", dict(total=0, passed=0, failed=0, errors=0, skipped=0), [], ""
    try:
        overlay = None if variant.name == "starter" else task.path / "solutions" / variant.name
        work = workspace.materialize(task.path / "starter", overlay, run_dir / "work")
        workspace.copy_tree(task.path / "grader" / spec.grader, run_dir / "grader")
        workspace.copy_tree(config.ROOT / "graderlib", run_dir / "graderlib")
        env = {**os.environ, **config.DETERMINISM,
               "PYTHONPATH": os.pathsep.join([str(work), str(run_dir)])}
        if "postgres" in task.requires:
            env["DATABASE_URL"] = db.create_db(name)
            database_created = True
        command = [sys.executable, "-m", "pytest", str(run_dir / "grader"), "-q", "-p", "no:cacheprovider",
                   f"--rootdir={run_dir / 'grader'}", f"--confcutdir={run_dir / 'grader'}",
                   f"--junitxml={run_dir / 'junit.xml'}", "-o", "junit_family=xunit2"]
        proc = subprocess.run(command, cwd=work, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=task.timeout_seconds)
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])
        outcome, counts, failures = junit.parse(run_dir / "junit.xml", proc.returncode)
    except subprocess.TimeoutExpired:
        tail = f"timeout after {task.timeout_seconds}s"
    except Exception as exc:
        tail = f"{type(exc).__name__}: {exc}"
    finally:
        if database_created:
            try:
                db.drop_db(name)
            except Exception as exc:
                outcome, tail = "ERROR", tail + f"\nDB cleanup failed: {exc}"
        if not spec.keep_workspaces:
            shutil.rmtree(run_dir, ignore_errors=True)
    result = RunResult(task.id, variant.name, variant.kind, spec.grader, spec.repeat,
                       variant.expected, outcome,
                       verdict.decide(variant.expected, outcome, variant.must_fail, failures),
                       counts, failures, verdict.hits(variant.must_fail, failures),
                       round(time.perf_counter() - started, 3), tail, variant.predicted_naive)
    if spec.keep_workspaces:
        result.extra["workspace"] = str(run_dir)
    return asdict(result)
