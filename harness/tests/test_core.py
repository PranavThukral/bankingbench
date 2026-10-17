from dataclasses import replace
from pathlib import Path
import shutil

import pytest

from harness.discover import load_task
from harness.execute import run_one
from harness.junit import parse
from harness.model import RunSpec, Variant
from harness.verdict import decide
from harness.workspace import materialize, safe_path

TOY = Path(__file__).parent / "fixtures" / "toy_task"


def test_discover_schema(tmp_path):
    task = load_task(TOY)
    assert task.id == "toy_task"
    dest = tmp_path / "toy_task"
    shutil.copytree(TOY, dest)
    meta = dest / "task.toml"
    original = meta.read_text()
    for bad in [original.replace('title =', 'unexpected ='),
                original.replace('must_fail = ["test_other"]', ''),
                original.replace('id = "toy_task"', 'id = "another"')]:
        meta.write_text(bad)
        with pytest.raises(ValueError):
            load_task(dest)


def test_workspace_overlay(tmp_path):
    starter, overlay = tmp_path / "s", tmp_path / "o"
    starter.mkdir()
    overlay.mkdir()
    for name in ["replace", "keep", "remove"]:
        (starter / name).write_text("old")
    (overlay / "replace").write_text("new")
    (overlay / "__delete__.txt").write_text("remove\n")
    dest = materialize(starter, overlay, tmp_path / "work")
    assert (dest / "replace").read_text() == "new"
    assert (dest / "keep").exists() and not (dest / "remove").exists()
    for bad in ["../escape", "/escape", "C:\\escape", "..\\escape"]:
        with pytest.raises(ValueError):
            safe_path(dest, bad)
    (overlay / "__delete__.txt").write_text("../escape")
    with pytest.raises(ValueError):
        materialize(starter, overlay, tmp_path / "bad")


@pytest.mark.parametrize("body,code,outcome", [
    ('<testcase name="a"/>', 0, "PASS"),
    ('<testcase name="a"><failure/></testcase>', 1, "FAIL"),
    ('<testcase name="a"><error/></testcase>', 2, "ERROR"),
    ('', 5, "ERROR"),
    ('<testcase name="a"><skipped/></testcase>', 0, "FAIL"),
    ('<testcase name="a"/>', 4, "ERROR"),
])
def test_junit_parse(tmp_path, body, code, outcome):
    path = tmp_path / "junit.xml"
    path.write_text(f"<testsuites><testsuite>{body}</testsuite></testsuites>")
    assert parse(path, code)[0] == outcome


@pytest.mark.parametrize("expected,outcome,must,failed,want", [
    ("PASS", "PASS", [], [], "ok"),
    ("FAIL", "FAIL", [], [], "ok"),
    ("FAIL", "FAIL", ["test_x"], ["m::test_x[1]"], "ok"),
    ("FAIL", "FAIL", ["test_x"], ["m::test_y"], "ok_wrong_reason"),
    ("FAIL", "PASS", [], [], "false_pass"),
    ("PASS", "FAIL", [], [], "false_fail"),
    ("PASS", "ERROR", [], [], "infra_error"),
    ("FAIL", "ERROR", [], [], "infra_error"),
])
def test_verdict_table(expected, outcome, must, failed, want):
    assert decide(expected, outcome, must, failed) == want


def test_run_one_toy_task():
    task = load_task(TOY)
    variants = {v.name: v for v in task.variants}
    assert run_one(RunSpec(task, variants["reference"], "final"))["verdict"] == "ok"
    assert run_one(RunSpec(task, variants["wrong_constant"], "naive"))["verdict"] == "false_pass"
    assert run_one(RunSpec(task, variants["wrong_constant"], "final"))["verdict"] == "ok"
    assert run_one(RunSpec(task, Variant("starter", "reference"), "final"))["verdict"] == "false_fail"


def test_timeout_is_error(tmp_path):
    path = tmp_path / "toy_task"
    shutil.copytree(TOY, path)
    (path / "grader/final/test_hidden.py").write_text("import time\ndef test_slow():\n    time.sleep(10)\n")
    task = replace(load_task(path), timeout_seconds=0.2)
    result = run_one(RunSpec(task, task.variants[1], "final"))
    assert result["verdict"] == "infra_error"
    assert "timeout" in result["stderr_tail"]
