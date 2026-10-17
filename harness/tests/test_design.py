"""Meta-tests for the design-level realism checks: ref_diff_lines, regressive_wrong, S1 package LOC."""
import shutil

import pytest

from harness.check_done import package_loc, design_ok, LOC_MAX, LOC_MIN
from harness.check_realism import ref_diff_lines, diff_floor, regressive_wrong, design_rows
from harness.discover import load_task
from harness.tests.test_core import TOY


def make_task(tmp_path, difficulty="easy", reference_body=None, rationale=None, notes=None, extra_toml=""):
    root = tmp_path / "toy_task"
    shutil.copytree(TOY, root, ignore=shutil.ignore_patterns("__pycache__"))
    meta = (root / "task.toml").read_text()
    meta = meta.replace('difficulty = "easy"', f'difficulty = "{difficulty}"')
    if rationale is not None:
        meta += f'regression_rationale = "{rationale}"\n'
    (root / "task.toml").write_text(meta + extra_toml)
    if reference_body is not None:
        (root / "solutions/reference/toy.py").write_text(reference_body)
    if notes is not None:
        (root / "NOTES.md").write_text(notes)
    return root


def test_ref_diff_counts_added_and_removed_py_lines(tmp_path):
    root = make_task(tmp_path)
    # starter has 2 lines; the reference replaces one line (1 removed + 1 added).
    assert ref_diff_lines(load_task(root)) == 2
    (root / "solutions/reference/toy.py").write_text("def increment(n):\n    a = n\n    b = a + 1\n    return b\n")
    # "return n" removed (1); three new lines added (3).
    assert ref_diff_lines(load_task(root)) == 4


def test_ref_diff_counts_new_files_and_deletions_but_not_other_files(tmp_path):
    root = make_task(tmp_path)
    reference = root / "solutions/reference"
    (reference / "helper.py").write_text("A = 1\nB = 2\nC = 3\n")
    (reference / "notes.txt").write_text("x\ny\nz\nw\n")
    assert ref_diff_lines(load_task(root)) == 2 + 3
    (root / "starter/legacy.py").write_text("X = 1\nY = 2\n")
    (reference / "__delete__.txt").write_text("legacy.py\n")
    assert ref_diff_lines(load_task(root)) == 2 + 3 + 2


def test_ref_diff_is_zero_for_an_identical_reference(tmp_path):
    root = make_task(tmp_path)
    shutil.copyfile(root / "starter/toy.py", root / "solutions/reference/toy.py")
    assert ref_diff_lines(load_task(root)) == 0


def test_diff_floor_by_difficulty(tmp_path):
    floors = {d: diff_floor(load_task(make_task(tmp_path / d, d))) for d in ("easy", "medium", "hard")}
    assert floors == {"easy": 12, "medium": 25, "hard": 40}


def test_regressive_wrong_is_the_must_fail_set_the_starter_passes(tmp_path):
    variant = next(v for v in load_task(make_task(tmp_path)).variants if v.name == "wrong_constant")
    assert regressive_wrong(variant, ["g.py::test_other"]) == []
    assert regressive_wrong(variant, []) == ["test_other"]
    # parametrised ids are matched on the bare test name
    assert regressive_wrong(variant, ["g.py::test_other[1]"]) == []
    assert regressive_wrong(variant, ["g.py::test_unrelated"]) == ["test_other"]


BIG = "def increment(n):\n" + "".join(f"    v{i} = n + {i}\n" for i in range(14)) + "    return n + 1\n"


def rows_for(root, starter_failed):
    return design_rows([load_task(root)], {"toy_task": starter_failed})[0]


def test_design_rows_fail_below_the_diff_floor(tmp_path):
    row = rows_for(make_task(tmp_path), ["g.py::test_other"])
    assert row["ref_diff_lines"] == 2 and row["floor"] == 12
    assert not row["diff_ok"] and not row["ok"]


def test_design_rows_pass_with_enough_diff_and_a_non_regressive_wrong(tmp_path):
    row = rows_for(make_task(tmp_path, reference_body=BIG), ["g.py::test_other"])
    assert row["diff_ok"] and row["ok"]
    assert row["regressive"]["wrong_constant"]["tests"] == []


def test_design_rows_require_a_rationale_for_a_regressive_wrong(tmp_path):
    row = rows_for(make_task(tmp_path, reference_body=BIG), [])
    assert row["regressive"]["wrong_constant"]["tests"] == ["test_other"]
    assert not row["ok"]


def test_design_rows_require_the_rationale_in_notes(tmp_path):
    why = "A first implementation naturally hard-codes the answer."
    missing = make_task(tmp_path / "a", reference_body=BIG, rationale=why)
    assert not rows_for(missing, [])["ok"]
    logged = make_task(tmp_path / "b", reference_body=BIG, rationale=why,
                       notes=f"## Regression rationale\n\nwrong_constant: {why}\n")
    assert rows_for(logged, [])["ok"]


def test_design_rows_reject_a_stale_rationale(tmp_path):
    why = "Not actually regressive."
    root = make_task(tmp_path, reference_body=BIG, rationale=why,
                     notes=f"wrong_constant: {why}\n")
    assert not rows_for(root, ["g.py::test_other"])["ok"]


def test_design_ok_uses_source_diff_not_the_receipt(tmp_path):
    task = load_task(make_task(tmp_path))
    forged = {"design": [{"task": "toy_task", "ok": True}]}
    assert not design_ok(forged, [task])
    assert not design_ok({}, [task])


@pytest.mark.parametrize("bad", ['regression_rationale = ""', 'regression_rationale = 3'])
def test_discover_rejects_bad_rationale_on_wrong_variant(tmp_path, bad):
    root = make_task(tmp_path)
    meta = (root / "task.toml").read_text() + bad + "\n"
    (root / "task.toml").write_text(meta)
    with pytest.raises(ValueError):
        load_task(root)


def test_discover_rejects_rationale_on_non_wrong_variant(tmp_path):
    root = make_task(tmp_path)
    meta = (root / "task.toml").read_text().replace(
        '[variants.reference]\nkind = "reference"', '[variants.reference]\nkind = "reference"\nregression_rationale = "x"')
    (root / "task.toml").write_text(meta)
    with pytest.raises(ValueError):
        load_task(root)


def test_package_loc_excludes_tests_and_conftest(tmp_path):
    root = make_task(tmp_path)
    starter = root / "starter"
    (starter / "pkg").mkdir()
    (starter / "pkg/mod.py").write_text("x = 1\n" * 10)
    (starter / "conftest.py").write_text("y = 1\n" * 50)
    (starter / "tests/test_more.py").write_text("def test_x():\n    pass\n" * 40)
    (starter / "pkg/tests").mkdir()
    (starter / "pkg/tests/test_inner.py").write_text("z = 1\n" * 30)
    # toy.py has 2 lines; only it and pkg/mod.py count.
    assert package_loc(load_task(root)) == 2 + 10
    assert (LOC_MIN, LOC_MAX) == (200, 600)
