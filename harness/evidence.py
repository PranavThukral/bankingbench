"""Content fingerprints tie validation receipts to the candidate and grader sources."""
import hashlib
import json
from pathlib import Path

from harness import config


def task_digest(task):
    digest = hashlib.sha256()
    files = [task.path / "task.toml", task.path / "PROBLEM.md"]
    for root in (task.path / "starter", task.path / "solutions", task.path / "grader", config.ROOT / "graderlib"):
        files += [p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    for path in sorted(files):
        digest.update(str(path.relative_to(config.ROOT)).replace("\\", "/").encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def fingerprints(tasks):
    return {t.id: task_digest(t) for t in tasks}


def matches(receipt, tasks):
    return all(receipt.get("task_digests", {}).get(t.id) == task_digest(t) for t in tasks)


def load(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
