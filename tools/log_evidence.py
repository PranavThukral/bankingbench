"""Append measured run summaries and fill real audit-history commit identifiers."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import ROOT
from harness.discover import discover
from harness.run_all import latest, summary


def sha():
    return subprocess.check_output(["git", "--git-dir=.audit-history", "--work-tree=.",
                                    "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["naive", "final"])
    parser.add_argument("task")
    args = parser.parse_args()
    task = discover(selected=args.task)[0]
    file = ROOT / "analysis/findings.md"
    text = file.read_text(encoding="utf-8")
    matrix = json.loads(latest().read_text(encoding="utf-8"))
    if args.phase == "naive":
        for run in matrix["runs"]:
            if run["verdict"] not in {"false_pass", "false_fail"}:
                continue
            variant = next(v for v in task.variants if v.name == run["variant"])
            anchor = f"{task.id}-{variant.name}"
            text += (f'\n<a id="{anchor}"></a>\n### {task.id} · {variant.name} · {run["verdict"]} under naive\n'
                     f'- **Naive grader commit:** {sha()} · **Hardened commit:** PENDING-{task.id}\n'
                     f'- **What slipped through:** {variant.bug or "The unmodified starter satisfies ordinary examples but omits required behavior."}\n'
                     '- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.\n'
                     f'- **Hardening:** add observable tests `{", ".join(variant.must_fail)}` plus the task invariants.\n'
                     '- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.\n')
    else:
        text = text.replace(f"PENDING-{task.id}", sha())
    text += f"\n#### {task.id} — measured {args.phase} summary (run {matrix['git_sha']})\n```text\n{summary(matrix)}\n```\n"
    file.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
