"""Render matrix.json as one self-contained, offline HTML report (inline CSS and fonts, no JavaScript)."""
import argparse
import base64
import difflib
from html import escape
import json
from pathlib import Path
from string import Template
import tomllib

from harness import config
from harness.run_all import latest

TEMPLATES = config.ROOT / "harness/templates"
COLUMNS = ("starter", "reference", "alt_valid")
# verdict -> (css tone, icon, short meaning)
TONES = {"ok": ("good", "✓", "as expected"), "ok_wrong_reason": ("warn", "~", "rejected for an undeclared reason"),
         "false_pass": ("bad", "✗", "false pass"), "false_fail": ("bad", "✗", "false fail"),
         "infra_error": ("bad", "!", "infrastructure error")}
OUTCOME = {"PASS": "accepted", "FAIL": "rejected", "ERROR": "error"}


def variant_diff(task_path, variant):
    overlay = task_path / "solutions" / variant
    lines = []
    for path in sorted(overlay.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            relative = path.relative_to(overlay)
            original = task_path / "starter" / relative
            before = original.read_text(encoding="utf-8").splitlines(True) if original.exists() else []
            after = path.read_text(encoding="utf-8").splitlines(True)
            lines.extend(difflib.unified_diff(before, after, f"starter/{relative}", f"{variant}/{relative}"))
    return "".join(lines)


def highlight_diff(text):
    out = []
    for line in text.splitlines():
        kind = ("meta" if line.startswith(("+++", "---")) else "add" if line.startswith("+")
                else "del" if line.startswith("-") else "hunk" if line.startswith("@@") else "")
        out.append(f'<span class="{kind}">{escape(line)}</span>' if kind else escape(line))
    return "\n".join(out) or "No changes against the starter."


def font_face(family, filename):
    data = base64.b64encode((TEMPLATES / "fonts" / filename).read_bytes()).decode("ascii")
    return (f"@font-face{{font-family:'{family}';font-style:normal;font-weight:400 700;font-display:swap;"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")


def task_title(path):
    try:
        return tomllib.loads((path / "task.toml").read_text(encoding="utf-8")).get("title", path.name)
    except (OSError, tomllib.TOMLDecodeError):
        return path.name


def outcome(run):
    if "outcome" in run:
        return run["outcome"]
    tests = run["tests"]
    return "PASS" if tests["total"] and tests["passed"] == tests["total"] else "FAIL"


def anchor(task, variant):
    return f"run-{task}-{variant}"


def badge(run, label):
    if run is None:
        return f'<span class="badge none"><b>{label}</b> not run</span>'
    tone, icon, _ = TONES.get(run["verdict"], TONES["infra_error"])
    tests = run["tests"]
    return (f'<span class="badge {tone}"><b>{label}</b><i aria-hidden="true">{icon}</i>'
            f'{OUTCOME.get(outcome(run), "error")}<small>{tests["passed"]}/{tests["total"]}</small></span>')


def failed_list(run):
    failed = run["failed_tests"]
    if not failed:
        total = run["tests"]["total"]
        return f'<p class="allpass">All {total} hidden test{"s" if total != 1 else ""} passed.</p>'
    hits = set(run.get("must_fail_hit") or [])
    items = []
    for test in failed:
        name = test.split("::")[-1]
        flag = ' <em class="tag">declared must_fail</em>' if name in hits else ""
        items.append(f"<li><code>{escape(test)}</code>{flag}</li>")
    return f'<ul class="failed">{"".join(items)}</ul>'


def run_panel(run, grader, caught):
    tone, icon, meaning = TONES.get(run["verdict"], TONES["infra_error"])
    tests = run["tests"]
    facts = [f'<dt>Verdict</dt><dd><span class="pill {tone}">{icon} {escape(run["verdict"])}</span> {meaning}</dd>',
             f'<dt>Expected</dt><dd>{escape(run.get("expected", "?"))}, observed {escape(outcome(run))}</dd>',
             f'<dt>Duration</dt><dd>{run.get("duration_s", 0):.2f} s</dd>']
    if grader == "naive" and run.get("predicted_naive"):
        match = "matched" if run["predicted_naive"] == run["verdict"] else "missed"
        facts.append(f'<dt>Prediction</dt><dd>{escape(run["predicted_naive"])} ({match})</dd>')
    if caught:
        facts.append('<dt>Hardening</dt><dd><a href="../../analysis/findings.md">caught by hardening</a></dd>')
    transcript = run.get("stderr_tail") or "No transcript was captured for this run."
    summary = f'{escape(run["variant"])}: {escape(run["verdict"])} {tests["passed"]}/{tests["total"]}'
    return (f'<details class="run"><summary><span class="grader">{grader.title()} grader</span>'
            f'<span class="pill {tone}">{icon} {summary}</span></summary><div class="db">'
            f'<h5>Failed tests</h5>{failed_list(run)}<dl class="facts">{"".join(facts)}</dl>'
            f'<details class="transcript"><summary>Pytest output (last 40 lines)</summary><div class="db">'
            f'<pre>{escape(transcript)}</pre></div></details></div></details>')


def render(matrix, tasks_root=config.TASKS):
    catalog_path = Path(tasks_root) / "catalog.toml"
    catalog = tomllib.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    runs = [r for r in matrix["runs"] if r.get("repeat", 0) == 0] or matrix["runs"]
    tasks = sorted({r["task"] for r in runs})
    index = {(r["task"], r["variant"], r["grader"]): r for r in runs}
    final = [r for r in runs if r["grader"] == "final"]
    naive = [r for r in runs if r["grader"] == "naive"]
    final_bad = [r for r in final if r["verdict"] != "ok"]

    def is_caught(r):
        prior = index.get((r["task"], r["variant"], "naive"), {})
        return r["grader"] == "final" and r["verdict"] == "ok" and prior.get("verdict") == "false_pass"

    caught = [r for r in final if is_caught(r)]
    wrong_naive = [r for r in naive if r["kind"] == "wrong"]
    wrong_final = [r for r in final if r["kind"] == "wrong"]
    valid_final = [r for r in final if r["kind"] in ("reference", "alt_valid")]

    def kpi(value, label, tone=""):
        return f'<div class="kpi {tone}"><span class="num">{value}</span><span class="lbl">{label}</span></div>'

    kpis = [kpi(f'{len(final) - len(final_bad)}/{len(final)}', "final verdicts as expected",
                "good" if not final_bad else "bad")]
    if naive:
        passed = sum(r["verdict"] == "false_pass" for r in wrong_naive)
        kpis.append(kpi(f"{passed}/{len(wrong_naive)}", "wrong solutions accepted by naive graders", "bad" if passed else ""))
    kpis.append(kpi(f'{sum(r["verdict"] == "false_pass" for r in wrong_final)}/{len(wrong_final)}',
                    "wrong solutions accepted by final graders"))
    kpis.append(kpi(f'{sum(r["verdict"] == "false_fail" for r in valid_final)}/{len(valid_final)}',
                    "valid solutions rejected by final graders"))

    task_rows = []
    for number, task in enumerate(tasks, 1):
        info = catalog.get(task, {})
        task_rows.append(f'<tr><td>{number:02d}</td><td>{escape(info.get("area", ""))}</td>'
                         f'<th scope="row"><a href="#task-{escape(task)}">'
                         f'{escape(task_title(Path(tasks_root) / task))}</a></th>'
                         f'<td>{escape(info.get("summary", ""))}</td></tr>')
    tasks_html = ('<section id="tasks"><h2>Tasks</h2><div class="scroll" tabindex="0" role="region" '
                  'aria-label="Tasks overview"><table class="task-overview"><thead><tr><th>Number</th><th>Area</th>'
                  '<th>Title</th><th>Summary</th></tr></thead><tbody>' + "".join(task_rows) + '</tbody></table></div></section>')
    body = []
    if final_bad:
        rows = "".join(f'<li><a href="#{anchor(r["task"], r["variant"])}">{escape(r["task"])} · {escape(r["variant"])}'
                       f'</a> — {escape(r["verdict"])}{failed_list(r)}</li>' for r in final_bad)
        body.append(f'<section class="alert"><h2>FINAL DEVIATIONS — review these first</h2><ul>{rows}</ul></section>')

    caught_html = ""
    if caught:
        rows = []
        for r in caught:
            prior = index[(r["task"], r["variant"], "naive")]
            tests = "".join(f"<li><code>{escape(t.split('::')[-1])}</code></li>" for t in r["failed_tests"])
            rows.append(f'<tr><td><a href="#{anchor(r["task"], r["variant"])}"><code>{escape(r["task"])}</code><br>'
                        f'<code class="variant">{escape(r["variant"])}</code></a></td>'
                        f'<td>{badge(prior, "Naive")}</td><td>{badge(r, "Final")}</td><td><ul class="failed">{tests}</ul></td></tr>')
        caught_html = ('<section id="caught"><h2>What hardening caught</h2><p class="lede">Each row is a wrong solution (or an '
                    'unmodified starter) that the naive grader accepted, alongside the final-grader tests that '
                    'reject it. Each one is caught by hardening and logged in <a href="../../analysis/findings.md">'
                    'findings.md</a>.</p><div class="scroll"><table class="caught"><thead><tr><th>Task · solution</th>'
                    '<th>Naive</th><th>Final</th><th>Final tests that fail</th></tr></thead><tbody>'
                    + "".join(rows) + "</tbody></table></div></section>")

    wrong_by_task = {t: sorted({r["variant"] for r in runs if r["task"] == t and r["kind"] == "wrong"}) for t in tasks}
    width = max((len(v) for v in wrong_by_task.values()), default=0)
    head = "".join(f"<th>{c.replace('_', ' ').capitalize()}</th>" for c in COLUMNS)
    head += f'<th colspan="{width}">Wrong solutions</th>' if width else ""
    grid = []
    for task in tasks:
        cells = []
        for variant in [*COLUMNS, *wrong_by_task[task]]:
            n, f = index.get((task, variant, "naive")), index.get((task, variant, "final"))
            if n is None and f is None:
                cells.append('<td class="empty">—</td>')
                continue
            tip = " · ".join(f'{variant}: {r["verdict"]} {r["tests"]["passed"]}/{r["tests"]["total"]} ({g})'
                             for g, r in (("naive", n), ("final", f)) if r)
            label = f'<code class="variant">{escape(variant.removeprefix("wrong_"))}</code>' if variant.startswith("wrong_") else ""
            mark = '<span class="caught-tag">caught by hardening</span>' if f and is_caught(f) else ""
            cells.append(f'<td><a class="cell" href="#{anchor(task, variant)}" title="{escape(tip)}">{label}'
                         f'{badge(n, "Naive") if naive else ""}{badge(f, "Final")}{mark}</a></td>')
        cells.extend('<td class="empty"></td>' for _ in range(width - len(wrong_by_task[task])))
        grid.append(f'<tr id="matrix-{escape(task)}"><th scope="row"><code>{escape(task)}</code>'
                    f'<span class="sub">{escape(catalog.get(task, {}).get("area", task_title(Path(tasks_root) / task)))}</span></th>{"".join(cells)}</tr>')
    body.append('<section id="matrix"><h2>Hardening matrix</h2><p class="lede">One row per task, one column per solution. '
                'Each cell shows what the naive and final graders did with that solution; select it for the failing '
                'tests and pytest output.</p>'
                '<ul class="legend"><li><span class="pill good">✓</span> as expected</li>'
                '<li><span class="pill bad">✗</span> false pass, false fail or error</li>'
                '<li><span class="pill warn">~</span> rejected, but not by a declared test</li></ul>'
                f'<div class="scroll"><table class="matrix"><thead><tr><th>Task</th>{head}</tr></thead>'
                f'<tbody>{"".join(grid)}</tbody></table></div></section>')

    body.append(caught_html)

    panels = []
    for task in tasks:
        path = Path(tasks_root) / task
        parts = []
        info = catalog.get(task, {})
        if info.get("summary"):
            parts.append(f'<p class="task-summary">{escape(info["summary"])}</p>')
        if info.get("checks"):
            checks = "".join(f'<li>{escape(check)}</li>' for check in info["checks"])
            parts.append(f'<h3 class="checks-heading">What the hardened grader checks</h3><ul class="checks">{checks}</ul>')
        for name, label in (("PROBLEM.md", "Ticket (PROBLEM.md)"), ("NOTES.md", "Reviewer notes (NOTES.md)")):
            text = (path / name).read_text(encoding="utf-8") if (path / name).exists() else "Fixture text"
            parts.append(f'<details><summary>{label}</summary><div class="db"><pre class="doc">{escape(text)}</pre></div></details>')
        variants = [*COLUMNS, *wrong_by_task[task]]
        for variant in [v for v in variants if any((task, v, g) in index for g in ("naive", "final"))]:
            sample = index.get((task, variant, "final")) or index.get((task, variant, "naive"))
            graders = "".join(run_panel(index[(task, variant, g)], g, g == "final" and is_caught(index[(task, variant, g)]))
                              for g in ("final", "naive") if (task, variant, g) in index)
            diff = ""
            if variant != "starter":
                diff = (f'<details class="diff"><summary>Diff against the starter</summary><div class="db"><pre>'
                        f'{highlight_diff(variant_diff(path, variant))}</pre></div></details>')
            parts.append(f'<div class="variant-block"><div id="{anchor(task, variant)}" class="anchor"></div>'
                         f'<h4><code>{escape(variant)}</code><span class="kind">{escape(sample["kind"])}</span></h4>'
                         f'{graders}{diff}</div>')
        panels.append(f'<details class="task" id="task-{escape(task)}"><summary><code>{escape(task)}</code><span class="sub">'
                      f'{escape(task_title(path))}</span></summary><div class="db">{"".join(parts)}</div></details>')
    body.append('<section><h2>Runs by task</h2><p class="lede">Each run lists its failed tests first, then the '
                'tail of its pytest output.</p>' + "".join(panels) + "</section>")

    env = matrix.get("env", {})
    facts = [("Commit", matrix.get("git_sha", "unknown")),
             ("Working tree", "dirty" if matrix.get("dirty") else "clean"),
             ("Generated", str(matrix.get("generated_at", "fixture")).replace("T", " ")[:19] + " UTC"),
             ("Runs", f'{len(matrix["runs"])}' + (f' in {matrix["wall_s"]:.0f} s' if matrix.get("wall_s") else "")),
             *[(k.replace("_", " ").capitalize(), str(v)) for k, v in env.items()]]
    facts_html = "".join(f"<dt>{escape(k)}</dt><dd><code>{escape(v)}</code></dd>" for k, v in facts)
    template = Template((TEMPLATES / "report.html").read_text(encoding="utf-8"))
    return template.substitute(
        fonts=font_face("Source Serif 4", "source-serif-4.woff2") + font_face("JetBrains Mono", "jetbrains-mono.woff2"),
        facts=facts_html, kpis="".join(kpis), tasks=tasks_html, body="\n".join(body), status=escape(matrix.get("status", "private draft")),
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--in", dest="source", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    source = args.source or latest()
    output = args.out or source.with_name("report.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(json.loads(source.read_text(encoding="utf-8"))), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
