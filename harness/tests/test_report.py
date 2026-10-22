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


def test_counts_are_labelled_and_runtest_is_hidden():
    from harness.tests.test_core import TOY
    data = fixture()
    data["runs"][2]["failed_tests"] = ["test_hidden.TestJournal::runTest", "test_hidden::test_other"]
    html = render(data, TOY.parent, findings="missing.md")
    assert 'title="passed 1 of 2 tests"' in html
    assert "hidden tests passed / total" in html
    visible = re.sub(r"base64,[A-Za-z0-9+/=]+", "", html)
    assert "runTest" not in re.sub(r"<pre>.*?</pre>", "", visible, flags=re.S)
    data["runs"][2]["failed_tests"] = ["test_hidden.TestJournal::runTest"]
    assert "stateful property test" in render(data, TOY.parent, findings="missing.md")


def test_caught_links_use_findings_anchors(tmp_path):
    from harness.tests.test_core import TOY
    findings = tmp_path / "findings.md"
    findings.write_text('<a id="toy_task-wrong_constant"></a>\n## entry\n', encoding="utf-8")
    html = render(fixture(), TOY.parent, findings=findings)
    assert '../../analysis/findings.md#toy_task-wrong_constant"' in html
    plain = render(fixture(), TOY.parent, findings=tmp_path / "absent.md")
    assert "findings.md#toy_task" not in plain and '../../analysis/findings.md"' in plain


def test_matrix_stacks_on_narrow_screens():
    from harness.tests.test_core import TOY
    html = render(fixture(), TOY.parent, findings="missing.md")
    assert "@media (max-width:700px)" in html and 'data-label="Reference"' in html


def test_heldout_section(tmp_path):
    import json
    from harness.tests.test_core import TOY
    runs = [dict(task="01_toy", expect="reject", outcome="FAIL"), dict(task="01_toy", expect="reject", outcome="PASS"),
            dict(task="01_toy", expect="accept", outcome="PASS")]
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(dict(runs=[dict(task="01_toy", expect="reject", outcome="PASS")] * 4)))
    assert 'id="heldout"' not in render(fixture(), TOY.parent, findings="missing.md")
    assert 'id="heldout"' not in render(fixture(), TOY.parent, heldout={}, findings="missing.md")
    html = render(fixture(), TOY.parent, heldout=dict(runs=runs, baseline_receipt=str(baseline)), findings="missing.md")
    section = html.split('<section id="heldout">', 1)[1].split("</section>", 1)[0]
    assert "1 of 2" in section and "1 of 1" in section
    assert "1/2 (50.0%)" in section and "0/4 (0.0%)" in section
    broken = render(fixture(), TOY.parent, heldout=dict(runs=runs, baseline_receipt="nope.json"), findings="missing.md")
    assert "could not be read" in broken
