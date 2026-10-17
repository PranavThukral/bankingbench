import argparse
import difflib
from html import escape
import json
from pathlib import Path
from string import Template

from harness import config
from harness.run_all import latest


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


def render(matrix, tasks_root=config.TASKS):
    runs = matrix["runs"]
    task_ids = sorted({r["task"] for r in runs})
    final_bad = [r for r in runs if r["grader"] == "final" and r["verdict"] != "ok"]
    index = {(r["task"], r["variant"], r["grader"]): r for r in runs}
    sections = []
    for grader in ("final", "naive"):
        if not any(r["grader"] == grader for r in runs):
            continue
        sections.append(f"<h2>{grader.title()} matrix</h2><table><thead><tr><th>Task</th>"
                        "<th>starter</th><th>reference</th><th>alt_valid</th><th>wrong variants</th></tr></thead><tbody>")
        for task in task_ids:
            def cell(variant):
                run = index.get((task, variant, grader))
                if run is None:
                    return "<td>not run</td>"
                tests = run["tests"]
                prior = index.get((task, variant, "naive"), {})
                caught = grader == "final" and run["verdict"] == "ok" and prior.get("verdict") == "false_pass"
                anchor = f"{task}-{variant}"
                annotation = f'<a href="../../analysis/findings.md#{anchor}">caught by hardening</a>' if caught else ""
                prediction = run.get("predicted_naive", "") if grader == "naive" else ""
                detail = "\n".join(run["failed_tests"]) or "No failed test ids"
                return (f'<td class="{escape(run["verdict"])}"><details><summary>{escape(variant)}: '
                        f'{escape(run["verdict"])} {tests["passed"]}/{tests["total"]}</summary>'
                        f'<pre>{escape(detail)}</pre><p>Prediction: {escape(prediction)}</p></details>{annotation}</td>')
            sections.append(f'<tr id="{grader}-{task}"><th>{escape(task)}</th>')
            sections.extend(cell(v) for v in ("starter", "reference", "alt_valid"))
            wrong = sorted({r["variant"] for r in runs if r["task"] == task and r["kind"] == "wrong"})
            sections.append("<td><table><tr>" + "".join(cell(v) for v in wrong) + "</tr></table></td></tr>")
        sections.append("</tbody></table>")
    for task in task_ids:
        path = Path(tasks_root) / task
        sections.append(f"<details><summary>{escape(task)} — ticket, notes and diffs</summary>")
        for name in ("PROBLEM.md", "NOTES.md"):
            text = (path / name).read_text(encoding="utf-8") if (path / name).exists() else "Fixture text"
            sections.append(f"<h3>{name}</h3><pre>{escape(text)}</pre>")
        for variant in sorted({r["variant"] for r in runs if r["task"] == task and r["variant"] != "starter"}):
            sections.append(f"<details><summary>{escape(variant)} diff</summary><pre>"
                            f"{escape(variant_diff(path, variant))}</pre></details>")
        sections.append("</details>")
    template = Template((config.ROOT / "harness/templates/report.html").read_text(encoding="utf-8"))
    return template.substitute(
        sha=escape(matrix.get("git_sha", "unknown")), stamp=escape(matrix.get("generated_at", "fixture")),
        total=str(len(runs)), deviations=str(len(final_bad)),
        banner='<p class="alert">FINAL DEVIATIONS — review failures below</p>' if final_bad else '',
        body="\n".join(sections), env=escape(json.dumps(matrix.get("env", {}))),
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
