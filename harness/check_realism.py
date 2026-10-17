import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from harness import config, db
from harness.discover import discover
from harness.evidence import fingerprints
from harness.workspace import materialize


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
    config.RESULTS.mkdir(exist_ok=True)
    receipt = dict(task_digests=fingerprints(tasks), rows=rows)
    (config.RESULTS / "realism.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return int(not rows or any(not r["ok"] for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
