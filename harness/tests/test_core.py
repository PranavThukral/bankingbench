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


def test_forged_junit_is_not_a_pass():
    """Review F17: candidate code that rewrites junit.xml and exits 0 must not be accepted."""
    task = load_task(TOY)
    forge = Variant("wrong_forge_junit", "wrong", ("test_other",), "rewrites junit.xml", "infra_error")
    overlay = TOY / "solutions/wrong_forge_junit"
    for grader in ("naive", "final"):
        result = run_one(RunSpec(task, forge, grader), overlay)
        assert result["outcome"] != "PASS", result
        assert result["verdict"] == "infra_error", result
        assert "verdict integrity" in result["stderr_tail"]


def test_candidate_env_is_allow_listed(monkeypatch, tmp_path):
    from harness.manifest import allowed_env
    monkeypatch.setenv("PG_ADMIN_URL", "postgresql://postgres:secret@h/db")
    monkeypatch.setenv("SOME_API_TOKEN", "x")
    env = allowed_env(DATABASE_URL="u")
    assert "PG_ADMIN_URL" not in env and "SOME_API_TOKEN" not in env
    assert env["DATABASE_URL"] == "u" and env["PYTHONHASHSEED"] == "0"


@pytest.mark.parametrize("mode,found,want", [
    ("collected", [("m", "test_a"), ("m", "test_b")], "PASS"),
    ("collected", [("m", "test_a")], "ERROR"),                               # missing
    ("collected", [("m", "test_a"), ("m", "test_b"), ("m", "test_c")], "ERROR"),  # extra
    ("collected", [("m", "test_a"), ("m", "test_x")], "ERROR"),              # renamed
    ("ast", [("m", "test_a[1]"), ("m", "test_a[2]"), ("m", "test_b")], "PASS"),
    ("ast", [("m", "test_a")], "ERROR"),
])
def test_manifest_enforced(tmp_path, mode, found, want):
    from harness.junit import parse_checked
    cases = "".join(f'<testcase classname="{c}" name="{n}"/>' for c, n in found)
    path = tmp_path / "junit.xml"
    path.write_text(f"<testsuites><testsuite>{cases}</testsuite></testsuites>")
    manifest = {"mode": mode, "ids": [["m", "test_a"], ["m", "test_b"]]}
    out = f"{len(found)} passed in 0.1s"
    assert parse_checked(path, 0, manifest, out)[0] == want


def test_exit_code_and_summary_cross_checks(tmp_path):
    from harness.junit import parse_checked
    path = tmp_path / "junit.xml"
    path.write_text('<testsuites><testsuite><testcase classname="m" name="a"><failure/></testcase></testsuite></testsuites>')
    assert parse_checked(path, 1, None, "1 failed in 0.1s")[0] == "FAIL"
    assert parse_checked(path, 0, None, "1 failed in 0.1s")[0] == "ERROR"      # exit 0 but a failure
    assert parse_checked(path, 1, None, "1 passed in 0.1s")[0] == "ERROR"      # summary disagrees
    assert parse_checked(path, 1, None, "")[0] == "ERROR"                      # no summary at all
    path.write_text('<testsuites><testsuite><testcase classname="m" name="a"/></testsuite></testsuites>')
    assert parse_checked(path, 1, None, "1 passed in 0.1s")[0] == "ERROR"      # exit 1 but nothing failed


def test_preflight_messages(monkeypatch):
    from harness import db
    monkeypatch.delenv("PG_ADMIN_URL", raising=False)
    assert "PG_ADMIN_URL is not set" in db.preflight()
    monkeypatch.setenv("PG_ADMIN_URL", "postgresql://postgres@127.0.0.1:1/postgres")
    message = db.preflight()
    assert "PG_ADMIN_URL" in message and "README" in message
    assert db.preflight(needs_postgres=False) is None


def test_run_all_preflight_exit_2_and_unknown_task(monkeypatch, capsys, tmp_path):
    from harness import run_all
    monkeypatch.setenv("PG_ADMIN_URL", "postgresql://postgres@127.0.0.1:1/postgres")
    assert run_all.main(["--tasks", "01", "--out", str(tmp_path)]) == 2
    assert "Preflight failed" in capsys.readouterr().err
    assert run_all.main(["--tasks", "99", "--out", str(tmp_path)]) == 2
    assert "valid ids" in capsys.readouterr().out


def test_summary_splits_wrong_and_starter():
    from harness.run_all import summary
    row = lambda kind: dict(grader="naive", verdict="false_pass", kind=kind)  # noqa: E731
    text = summary(dict(runs=[row("wrong"), row("wrong"), row("starter")], flips=[]))
    assert "naive_false_pass_wrong=2" in text and "naive_false_pass_starter=1" in text


def test_cleanup_failure_is_logged(monkeypatch, capsys):
    import harness.execute as execute

    real = shutil.rmtree

    def failing_rmtree(path, onexc=None, **kw):
        onexc(None, str(path), PermissionError("locked"))
        real(path, ignore_errors=True)  # do not leak the directory from the test itself
    monkeypatch.setattr(execute.shutil, "rmtree", failing_rmtree)
    task = load_task(TOY)
    result = run_one(RunSpec(task, {v.name: v for v in task.variants}["reference"], "final"))
    assert result["verdict"] == "ok"
    assert "workspace cleanup failed" in result["stderr_tail"]
    assert "workspace cleanup failed" in capsys.readouterr().err
