"""Meta-tests for pack-level checks: Python 3.12 lint and the closed requirements lock."""
from pathlib import Path
import sys

import pytest

from harness.check_realism import lint_py312

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import check_lock  # noqa: E402

LOCK = Path(__file__).resolve().parents[2] / "requirements.lock"


def test_lint_py312_accepts_clean_code_and_rejects_a_pyflakes_error(tmp_path):
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks" / "ok.py").write_text("x = 1\n")
    assert lint_py312(tmp_path)["ok"]
    (tmp_path / "tasks" / "bad.py").write_text("import os\n")
    result = lint_py312(tmp_path)
    assert not result["ok"] and "F401" in result["output"]


def test_repository_lock_is_a_closed_explained_set():
    assert check_lock.problems(LOCK) == []


def test_lock_check_reports_a_missing_and_a_stray_package(tmp_path):
    lines = [line for line in LOCK.read_text(encoding="utf-8").splitlines() if not line.startswith("h11==")]
    lock = tmp_path / "requirements.lock"
    lock.write_text("\n".join(lines + ["left-pad==1.0"]) + "\n", encoding="utf-8")
    found = check_lock.problems(lock)
    assert any("missing from lock: h11" in item for item in found)
    assert any("unexplained package: left-pad" in item for item in found)


def test_lock_check_rejects_unpinned_lines_and_windows_only_marker_on_a_linux_dependency(tmp_path):
    bad = tmp_path / "unpinned.lock"
    bad.write_text("pytest>=8\n", encoding="utf-8")
    with pytest.raises(ValueError):
        check_lock.parse_lock(bad)
    text = LOCK.read_text(encoding="utf-8").replace("h11==0.16.0 ", 'h11==0.16.0 ; sys_platform == "win32" ')
    marked = tmp_path / "marked.lock"
    marked.write_text(text, encoding="utf-8")
    assert any("h11" in item and "Windows-only" in item for item in check_lock.problems(marked))
