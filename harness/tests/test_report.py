from copy import deepcopy
import re

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
    visible = re.sub(r"base64,[A-Za-z0-9+/=]+", "", html)  # embedded font bytes can spell anything
    assert "None" not in visible and "nan" not in visible
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


def test_tasks_overview_without_catalog():
    from harness.tests.test_core import TOY
    html = render(fixture(), TOY.parent)
    assert '<section id="tasks"><h2>Tasks</h2>' in html
    assert '<a href="#task-toy_task">' in html
    assert '<details class="task" id="task-toy_task">' in html
    assert html.index('class="kpis"') < html.index('<section id="tasks">') < html.index('<section id="matrix">')


def test_catalog_descriptions_and_checks(tmp_path):
    task = tmp_path / "toy_task"
    task.mkdir()
    (task / "task.toml").write_text('title = "A toy task"', encoding="utf-8")
    (tmp_path / "catalog.toml").write_text(
        '[toy_task]\narea = "Payments & retries"\nsummary = "Charge <once>."\n'
        'checks = ["A retry does not charge twice", "Reject <script> markup"]\n', encoding="utf-8")
    html = render(fixture(), tmp_path)
    overview = html.split('<section id="tasks">', 1)[1].split('</section>', 1)[0]
    assert '<td>01</td>' in overview
    assert 'Payments &amp; retries' in overview and 'Charge &lt;once&gt;.' in overview
    assert '<a href="#task-toy_task">A toy task</a>' in overview
    matrix = html.split('<section id="matrix">', 1)[1].split('</section>', 1)[0]
    assert '<span class="sub">Payments &amp; retries</span>' in matrix
    panel = html.split('<details class="task" id="task-toy_task">', 1)[1]
    assert panel.index('Charge &lt;once&gt;.') < panel.index('What the hardened grader checks') < panel.index('Ticket (PROBLEM.md)')
    assert '<li>A retry does not charge twice</li>' in panel
    assert 'Reject &lt;script&gt; markup' in panel
    assert '<script' not in html
