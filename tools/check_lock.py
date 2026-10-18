"""Check that requirements.lock is a closed, explained set for the runner image.

The roots are the allow-listed packages (BLUEPRINT section 4.2). The dependency closure is read from
the installed distribution metadata and evaluated for Linux / Python 3.12 (the image) and for
Windows (the authoring host). The Dockerfile installs the lock with `pip install --no-deps -r`, so:
  * every package in the Linux closure must be pinned, with no marker that excludes Linux;
  * every pinned package must belong to the Linux or the Windows closure (no stray packages);
  * every pin must be exact (`==`).
"""
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
import re
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOTS = ["pytest", "hypothesis", "fastapi", "uvicorn", "httpx", "psycopg[binary]", "ruff"]
LINUX = {"sys_platform": "linux", "platform_system": "Linux", "os_name": "posix", "python_version": "3.12",
         "python_full_version": "3.12.7", "implementation_name": "cpython",
         "platform_python_implementation": "CPython", "platform_machine": "x86_64"}
WINDOWS = {**LINUX, "sys_platform": "win32", "platform_system": "Windows", "os_name": "nt",
           "platform_machine": "AMD64"}


def closure(roots, env):
    seen = {}

    def visit(requirement):
        name = canonicalize_name(requirement.name)
        try:
            dist = distribution(name)
        except PackageNotFoundError as exc:
            raise SystemExit(f"{name} is not installed; cannot compute the closure") from exc
        extras = set(requirement.extras)
        if name in seen and not extras:
            return
        seen[name] = dist.version
        for text in dist.requires or []:
            child = Requirement(text)
            if child.marker is not None:
                gated = "extra" in str(child.marker)
                wanted = [e for e in extras if child.marker.evaluate({**env, "extra": e})]
                if gated and not wanted:
                    continue
                if not gated and not child.marker.evaluate({**env, "extra": ""}):
                    continue
            if canonicalize_name(child.name) not in seen or child.extras:
                visit(child)

    for root in roots:
        visit(Requirement(root))
    return seen


def parse_lock(path):
    """Return {name: (version, marker_or_None)} from requirements.lock; comments and blanks are skipped."""
    pins = {}
    for number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.!+]+)\s*(?:;\s*(.+))?", line)
        if not match:
            raise ValueError(f"line {number}: not an exact pin: {raw!r}")
        pins[canonicalize_name(match.group(1))] = (match.group(2), match.group(3))
    return pins


def problems(lock_path, roots=ROOTS):
    pins = parse_lock(lock_path)
    linux, windows = closure(roots, LINUX), closure(roots, WINDOWS)
    out = []
    for name in sorted(set(linux) - set(pins)):
        out.append(f"missing from lock: {name} (needed on Linux / Python 3.12)")
    for name, (_, marker) in sorted(pins.items()):
        if name not in linux and name not in windows:
            out.append(f"unexplained package: {name} is not in any dependency closure")
        if name in linux and marker and "win32" in marker:
            out.append(f"{name} is needed on Linux but the lock marks it Windows-only")
    for name in sorted(set(windows) - set(linux)):
        if name in pins and not pins[name][1] and name != "tzdata":
            out.append(f"{name} is Windows-only and must carry a sys_platform marker")
    return out


def main(argv=None):
    path = Path(argv[0]) if argv else Path(__file__).resolve().parents[1] / "requirements.lock"
    found = problems(path)
    print("\n".join(found) if found else f"{path.name}: closed set, no unexplained packages")
    return int(bool(found))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
