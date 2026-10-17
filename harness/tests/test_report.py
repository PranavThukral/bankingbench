from copy import deepcopy

from harness.report import render


def fixture():
    return dict(git_sha="fixture123", generated_at="2026-10-17", env={}, runs=[
        dict(task="toy_task", variant="reference", kind="reference", grader="final",
             tests=dict(passed=1, total=1), failed_tests=[], verdict="ok"),
        dict(task="toy_task", variant="wrong_constant", kind="wrong", grader="naive",
             tests=dict(passed=1, total=1), failed_tests=[], verdict="false_pass",
             predicted_naive="false_pass"),
        dict(task="toy_task", variant="wrong_constant", kind="wrong", grader="final",
             tests=dict(passed=1, total=2), failed_tests=["test_hidden::test_other"], verdict="ok"),
    ])


def test_report_renders():
    from harness.tests.test_core import TOY
    html = render(fixture(), TOY.parent)
    assert "toy_task" in html and "fixture123" in html
    assert "caught by hardening" in html
    assert "FINAL DEVIATIONS" not in html
    assert "None" not in html and "nan" not in html
    assert '<script' not in html and 'src="http' not in html


def test_report_no_literals():
    from harness.tests.test_core import TOY
    first = fixture()
    second = deepcopy(first)
    second["runs"][0]["verdict"] = "false_fail"
    second["runs"][0]["tests"]["passed"] = 0
    before, after = render(first, TOY.parent), render(second, TOY.parent)
    assert before != after
    assert "FINAL DEVIATIONS" in after
    assert "reference: false_fail 0/1" in after
