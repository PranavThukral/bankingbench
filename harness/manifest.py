"""Expected-test manifest: which test ids a grader must report, derived without candidate code.

Primary mode: pytest --collect-only in a separate process whose PYTHONPATH holds the trusted starter
(never the candidate workspace). Fallback when collection needs more than the starter provides: parse
test function names with ast and require at least those functions (parametrize ids not enumerable).
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from harness import config
from harness.workspace import copy_tree

ENV_KEYS = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE",
            "LOCALAPPDATA", "APPDATA", "PATHEXT", "COMSPEC", "LANG", "LC_ALL")


def allowed_env(**extra):
    """Allow-listed environment for subprocesses that touch candidate or grader code."""
    env = {k: os.environ[k] for k in ENV_KEYS if k in os.environ}
    env.update(config.DETERMINISM)
    env.update(extra)
    return env


def nodeid_key(node):
    parts = node.split("::")
    module = parts[0].replace("\\", "/").removesuffix(".py").replace("/", ".")
    return [".".join([module, *parts[1:-1]]), parts[-1]]


def ast_ids(grader_dir):
    ids = []
    for path in sorted(Path(grader_dir).glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module = path.stem
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                ids.append([module, node.name])
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith("test"):
                        ids.append([f"{module}.{node.name}", item.name])
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) \
                    and node.value.attr == "TestCase":
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.startswith("Test"):
                        ids.append([f"{module}.{target.id}", "runTest"])
    return ids


def tree_digest(*roots):
    digest = hashlib.sha256()
    for root in roots:
        for p in sorted(Path(root).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                digest.update(p.relative_to(root).as_posix().encode())
                digest.update(p.read_bytes())
    return digest.hexdigest()


def build(grader_dir, starter_dir, graderlib_dir=None, timeout=120):
    """Return {"mode", "ids"}; uncached. starter_dir is trusted source, never a candidate workspace."""
    graderlib_dir = graderlib_dir or config.ROOT / "graderlib"
    with tempfile.TemporaryDirectory(prefix="manifest_", dir=_tmp()) as temp:
        root = Path(temp)
        copy_tree(grader_dir, root / "grader")
        copy_tree(graderlib_dir, root / "graderlib")
        (root / "empty").mkdir()
        env = allowed_env(PYTHONPATH=os.pathsep.join([str(Path(starter_dir).resolve()), str(root)]))
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(root / "grader"), "--collect-only", "-q", "-p", "no:cacheprovider",
             f"--rootdir={root / 'grader'}", f"--confcutdir={root / 'grader'}"],
            cwd=root / "empty", env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout)
        nodes = [line.strip() for line in proc.stdout.splitlines() if "::" in line and not line.startswith(" ")]
        if proc.returncode == 0 and nodes:
            return {"mode": "collected", "ids": [nodeid_key(n) for n in nodes]}
        ids = ast_ids(grader_dir)
        if not ids:
            raise RuntimeError("cannot derive an expected-test manifest: collection failed and no test functions found")
        return {"mode": "ast", "ids": ids}


def _tmp():
    config.TMP.mkdir(parents=True, exist_ok=True)
    return config.TMP


def cached(grader_dir, starter_dir, graderlib_dir=None):
    """build() memoised on disk by a digest of grader + graderlib + starter (written atomically)."""
    graderlib_dir = graderlib_dir or config.ROOT / "graderlib"
    key = tree_digest(grader_dir, graderlib_dir, starter_dir)[:24]
    path = _tmp() / f"manifest_{key}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    result = build(grader_dir, starter_dir, graderlib_dir)
    scratch = path.with_suffix(f".{os.getpid()}.tmp")
    scratch.write_text(json.dumps(result), encoding="utf-8")
    os.replace(scratch, path)
    return result
