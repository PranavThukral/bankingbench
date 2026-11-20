"""Export documented Harbor keys and execute the generated scripts for local oracle checks.

Schema authority: docs/reference/HARBOR_SCHEMA_NOTES.md, supplied official-doc excerpt.
No Harbor CLI or undocumented task.toml keys are used.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

from harness import config, db, manifest as manifests
from harness.discover import discover
from harness.evidence import fingerprints
from harness.workspace import copy_tree, materialize, safe_path

TOP_KEYS = {"schema_version", "multi_step_reward_strategy", "source", "task", "metadata", "verifier",
            "agent", "solution", "environment", "artifacts"}
TABLE_KEYS = {
    "task": {"name", "authors", "description", "keywords"},
    "verifier": {"timeout_sec", "network_mode", "allowed_hosts", "env", "user", "environment_mode"},
    "agent": {"timeout_sec", "network_mode", "allowed_hosts", "user"},
    "solution": {"env"},
    "environment": {"build_timeout_sec", "network_mode", "allowed_hosts", "docker_image", "os", "cpus",
                    "memory_mb", "storage_mb", "gpus", "gpu_types", "env", "healthcheck", "workdir"},
}


def validate_config(path):
    parsed = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    if parsed.keys() - TOP_KEYS:
        raise ValueError("undocumented Harbor top-level key")
    for name, allowed in TABLE_KEYS.items():
        if set(parsed.get(name, {})) - allowed:
            raise ValueError(f"undocumented Harbor {name} key")
    if not isinstance(parsed.get("schema_version"), str) or "/" not in parsed.get("task", {}).get("name", ""):
        raise ValueError("invalid Harbor task identity")
    if parsed.get("environment", {}).get("os") not in {"linux", "windows"}:
        raise ValueError("invalid Harbor OS")
    return parsed


VERIFIER = '''"""Generated offline verifier; all paths can be redirected for a native oracle run.

Mirrors harness/execute.py: expected-test manifest (tests/manifest.json, built at export time from the
trusted starter), JUnit + exit code + summary cross-check, allow-listed candidate environment, and a
per-run non-superuser database role. Tests are mounted only at verification time under Harbor.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import bb_db  # noqa: E402
import bb_junit  # noqa: E402

work = Path(os.environ.get("BB_APP_DIR", "/app"))
logs = Path(os.environ.get("BB_LOG_DIR", "/logs"))
output = logs / "verifier"
output.mkdir(parents=True, exist_ok=True)
manifest = json.loads((here / "manifest.json").read_text(encoding="utf-8"))
ALLOW = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "LOCALAPPDATA",
         "APPDATA", "PATHEXT", "COMSPEC", "LANG", "LC_ALL")
env = {k: os.environ[k] for k in ALLOW if k in os.environ}
env.update(PYTHONPATH=os.pathsep.join([str(work), str(here)]), PYTHONHASHSEED="0", TZ="UTC",
           PYTHONDONTWRITEBYTECODE="1", HYPOTHESIS_PROFILE="ci", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
admin = os.environ.get("PG_ADMIN_URL") or os.environ.get("DATABASE_URL")
handle = None
code, outcome, reason, counts = 2, "ERROR", "", {"passed": 0, "total": 0}
try:
    if manifest.get("requires_postgres"):
        if not admin:
            raise RuntimeError("PG_ADMIN_URL or DATABASE_URL must point at the PostgreSQL service")
        name, role, url = bb_db.create_run_db("verify_" + os.urandom(6).hex(), admin)
        handle = (name, role)
        env["DATABASE_URL"] = url  # the candidate never sees the admin URL
    command = [sys.executable, "-m", "pytest", str(here / "grader"), "-q", "-p", "no:cacheprovider",
               "--rootdir=" + str(here / "grader"), "--confcutdir=" + str(here / "grader"),
               "--basetemp=" + str(logs / "pytest-tmp"), "--junitxml=" + str(output / "junit.xml"),
               "-o", "junit_family=xunit2"]
    proc = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    code = proc.returncode
    outcome, counts, _, reason = bb_junit.parse_checked(output / "junit.xml", code, manifest, proc.stdout)
except Exception as exc:  # any infrastructure failure is a zero reward
    reason = f"{type(exc).__name__}: {exc}"
finally:
    if handle:
        try:
            bb_db.drop_run_db(*handle, admin)
        except Exception as exc:
            print(f"cleanup failed: {exc}", file=sys.stderr)
if reason:
    print(f"verdict integrity: {reason}", file=sys.stderr)
passed, total = counts["passed"], counts["total"]
reward = int(outcome == "PASS" and total > 0 and passed == total)
(output / "reward.txt").write_text(str(reward) + "\\n", encoding="utf-8")
(output / "reward.json").write_text(json.dumps({"passed": passed, "total": total, "reason": reason}) + "\\n",
                                    encoding="utf-8")
raise SystemExit(0 if outcome == "PASS" else 1 if outcome == "FAIL" else 2)
'''


def export_task(task, root):
    target = Path(root) / task.id
    if target.exists():
        # Only replace this task's generated output under the explicitly selected export root.
        if not target.resolve().is_relative_to(Path(root).resolve()) or target.is_symlink():
            raise ValueError("unsafe export destination")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    (target / "instruction.md").write_text((task.path / "PROBLEM.md").read_text(encoding="utf-8"), encoding="utf-8")
    q = json.dumps
    text = (f'schema_version = "1.3"\n# Only keys in HARBOR_SCHEMA_NOTES.md are emitted.\n'
            f'[task]\nname = {q("synthetic/" + task.id)}\nauthors = [{{name = "Pranav Thukral"}}]\n'
            f'description = {q(task.title)}\nkeywords = {q(list(task.tags))}\n'
            f'[metadata]\nsource_task = {q(task.id)}\n'
            f'mandatory = {str(task.mandatory).lower()}\ndifficulty = {q(task.difficulty)}\n'
            '# Authoring-only variants, must_fail and leak_terms remain in the source repository.\n'
            f'[verifier]\ntimeout_sec = {task.timeout_seconds}\nnetwork_mode = "no-network"\n'
            '# The agent timeout and the build/resource values below are chosen limits,\n'
            '# not values derived from measurements: timeout_sec 1800, build_timeout_sec 600, cpus 4,\n'
            '# memory_mb 4096, storage_mb 4096. Revisit them after real agent runs.\n'
            '[agent]\ntimeout_sec = 1800\nnetwork_mode = "no-network"\n'
            '[environment]\nbuild_timeout_sec = 600\nnetwork_mode = "no-network"\nos = "linux"\n'
            'cpus = 4\nmemory_mb = 4096\nstorage_mb = 4096\nworkdir = "/app"\n')
    (target / "task.toml").write_text(text, encoding="utf-8")
    environment = target / "environment"
    copy_tree(task.path / "starter", environment / "starter")
    (environment / "Dockerfile").write_text(
        '# ASSUMPTION: first build bankingbench-runner:local with the repository compose file.\n'
        'FROM bankingbench-runner:local\nWORKDIR /app\nCOPY starter/ /app/\nCMD ["sleep", "infinity"]\n', encoding="utf-8")
    if "postgres" in task.requires:
        (environment / "docker-compose.yaml").write_text('''# ASSUMPTION: Harbor uses service main and environment/ as its compose build context.
# Service naming and build conventions are not documented in the supplied schema notes.
# Validate these assumptions with the Harbor runtime before publication.
services:
  main:
    build: .
    command: ["sleep", "infinity"]
    environment:
      DATABASE_URL: postgresql://postgres:bankingbench@postgres:5432/bankingbench
    depends_on:
      postgres:
        condition: service_healthy
    networks: [private]
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: bankingbench
      POSTGRES_DB: bankingbench
    # Disposable synthetic data only.
    command: ["postgres", "-c", "fsync=off"]
    tmpfs: [/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d bankingbench"]
      interval: 1s
      timeout: 5s
      retries: 30
    networks: [private]
networks:
  private:
    internal: true
''', encoding="utf-8")
    tests = target / "tests"
    copy_tree(task.path / "grader/final", tests / "grader")
    copy_tree(config.ROOT / "graderlib", tests / "graderlib")
    (tests / "verify.py").write_text(VERIFIER, encoding="utf-8")
    # Trusted helpers and the expected-test manifest ship with the tests, never with the candidate.
    shutil.copyfile(config.ROOT / "harness/junit.py", tests / "bb_junit.py")
    shutil.copyfile(config.ROOT / "harness/db.py", tests / "bb_db.py")
    built = manifests.build(task.path / "grader/final", task.path / "starter")
    built["requires_postgres"] = "postgres" in task.requires
    (tests / "manifest.json").write_text(json.dumps(built, indent=1) + chr(10), encoding="utf-8")
    (tests / "test.sh").write_text('''#!/bin/sh
set -u
# No tests mount path is assumed: locate this script's own directory.
# ASSUMPTION: candidate work defaults to /app; BB_APP_DIR redirects native validation.
# /logs/verifier is documented; BB_LOG_DIR redirects it only for native validation.
TESTS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "${BB_PYTHON:-python}" "$TESTS_DIR/verify.py"
''', encoding="utf-8")
    solution = target / "solution"
    copy_tree(task.path / "solutions/reference", solution / "overlay")
    solve = '''#!/bin/sh
set -eu
# No solution mount path is assumed: locate the adjacent overlay from this script.
# ASSUMPTION: candidate work defaults to /app, matching environment.workdir.
SOLUTION_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=${BB_APP_DIR:-/app}
# Git Bash needs its POSIX spelling for native Windows paths passed via env.
if command -v cygpath >/dev/null 2>&1; then
    APP_DIR=$(cygpath -u "$APP_DIR")
fi
mkdir -p "$APP_DIR"
cp -R "$SOLUTION_DIR/overlay/." "$APP_DIR/"
'''
    deletion = task.path / "solutions/reference/__delete__.txt"
    if deletion.exists():
        for relative in deletion.read_text(encoding="utf-8").splitlines():
            if relative.strip():
                relative = relative.strip().replace("\\", "/")
                safe_path(target / "environment/starter", relative)
                # A literal relative path is enclosed in double quotes with shell metacharacters escaped.
                escaped = relative.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
                solve += f'rm -rf "$APP_DIR/{escaped}"\n'
        solve += 'rm -f "$APP_DIR/__delete__.txt"\n'
    (solution / "solve.sh").write_text(solve, encoding="utf-8")
    (tests / "test.sh").chmod(0o755)
    (solution / "solve.sh").chmod(0o755)
    validate_config(target / "task.toml")
    return target


def bash():
    found = shutil.which("bash") or shutil.which("sh")
    if not found:
        raise RuntimeError("oracle validation needs a POSIX shell (Git Bash on Windows)")
    return found


def validate_task(task, exported):
    rewards, details = {}, {}
    config.TMP.mkdir(parents=True, exist_ok=True)
    for solved in (True, False):
        with tempfile.TemporaryDirectory(prefix="oracle_", dir=config.TMP) as temporary:
            root = Path(temporary)
            work = materialize(exported / "environment/starter", None, root / "work")
            logs = root / "logs"
            env = {**os.environ, **config.DETERMINISM,
                   "BB_APP_DIR": work.as_posix(), "BB_LOG_DIR": logs.as_posix(),
                   "BB_PYTHON": Path(sys.executable).as_posix()}
            if "postgres" in task.requires:
                # As in Harbor's compose file, the verifier sees the service URL and makes its own
                # per-run role and database; the candidate-facing URL is created inside verify.py.
                env["DATABASE_URL"] = db.admin_url()
            if solved:
                apply = subprocess.run([bash(), (exported / "solution/solve.sh").as_posix()], env=env,
                                       capture_output=True, text=True, timeout=30)
                if apply.returncode:
                    raise RuntimeError(f"solve.sh failed: {apply.stdout} {apply.stderr}")
            run = subprocess.run([bash(), (exported / "tests/test.sh").as_posix()], cwd=work,
                                 env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                 timeout=task.timeout_seconds + 20)
            reward = int((logs / "verifier/reward.txt").read_text().strip())
            label = "reference" if solved else "starter"
            rewards[label + "_reward"] = reward
            details[label] = json.loads((logs / "verifier/reward.json").read_text())
            if reward != int(solved) or run.returncode not in {0, 1}:
                raise AssertionError(f"{label}: reward={reward}, exit={run.returncode}\n{run.stdout}\n{run.stderr}")
    return dict(task=task.id, **rewards, tests=details, validation="native generated solve.sh + test.sh")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export every task as a Harbor task directory.")
    parser.add_argument("--out", type=Path, default=config.ROOT / "dist/harbor",
                        help="export directory (default: dist/harbor)")
    parser.add_argument("--validate", action="store_true",
                        help="also run the generated solve.sh and test.sh natively: reference must score 1, starter 0")
    args = parser.parse_args(argv)
    tasks = discover()
    problem = db.preflight(args.validate and any("postgres" in t.requires for t in tasks))
    if problem:
        print(f"Preflight failed: {problem}", file=sys.stderr)
        return 2
    rows = []
    source = fingerprints(tasks)
    try:
        for task in tasks:
            output = export_task(task, args.out.resolve())
            if args.validate:
                rows.append(validate_task(task, output))
            print(f"{task.id}: {'oracle PASS (reference=1, starter=0)' if args.validate else 'exported'}", flush=True)
        if source != fingerprints(tasks):
            raise RuntimeError("task sources changed during oracle validation")
        if args.validate:
            config.RESULTS.mkdir(exist_ok=True)
            (config.RESULTS / "oracle.json").write_text(json.dumps(dict(task_digests=source, rows=rows), indent=2) + "\n", encoding="utf-8")
        return 0
    except Exception as exc:
        print(f"Export validation failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
