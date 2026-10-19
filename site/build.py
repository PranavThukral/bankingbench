"""Build site/index.html: a self-contained landing page whose numbers and code come from the repo.

Usage: python site/build.py [--matrix results/final/matrix.json] [--repo-url https://github.com/...]
Every figure on the page is computed in the browser from the embedded matrix; every code excerpt is
read from the task files at build time. Nothing is typed in by hand.
"""
import argparse
import ast
import base64
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
FONTS = ROOT / "harness/templates/fonts"
EXAMPLE = ROOT / "tasks/01_idempotent_payments"
RUN_FIELDS = ("task", "variant", "kind", "grader", "verdict", "outcome", "tests", "failed_tests",
              "must_fail_hit", "duration_s", "predicted_naive", "stderr_tail")


def font(family, filename, weights):
    data = base64.b64encode((FONTS / filename).read_bytes()).decode("ascii")
    return (f"@font-face{{font-family:'{family}';font-weight:{weights};font-style:normal;font-display:swap;"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")


def function_source(path, name):
    """Return the source of the first (possibly nested) function called name, dedented."""
    text = path.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            lines = ast.get_source_segment(text, node, padded=True).splitlines()
            indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
            return "\n".join(line[indent:] for line in lines)
    raise LookupError(f"{name} not found in {path}")


def ticket_rule(path, marker):
    """Return the bullet in PROBLEM.md that starts with marker, joined onto one line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.lstrip("- ").startswith(marker))
    out = [lines[start].lstrip("- ")]
    for line in lines[start + 1:]:
        if not line.startswith("  "):
            break
        out.append(line.strip())
    return " ".join(out)


def tasks():
    rows = {}
    for path in sorted((ROOT / "tasks").iterdir()):
        if not (path / "task.toml").exists():
            continue
        meta = tomllib.loads((path / "task.toml").read_text(encoding="utf-8"))
        rows[meta["id"]] = dict(
            title=meta["title"], difficulty=meta["difficulty"], tags=meta.get("tags", []),
            variants={name: {k: v for k, v in spec.items() if k in ("kind", "bug", "structural_difference", "must_fail")}
                      for name, spec in meta.get("variants", {}).items()})
    return rows


def build(matrix_path, repo_url):
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    runs = [{k: r.get(k) for k in RUN_FIELDS} for r in matrix["runs"] if r.get("repeat", 0) == 0]
    data = dict(
        meta={k: matrix.get(k) for k in ("git_sha", "dirty", "generated_at", "wall_s", "env")},
        runs=runs, tasks=tasks(), repo=repo_url or "",
        example=dict(
            task="01_idempotent_payments", variant="wrong_retry_race",
            rule=ticket_rule(EXAMPLE / "PROBLEM.md", "Concurrent identical duplicates"),
            wrong=function_source(EXAMPLE / "solutions/wrong_retry_race/app/main.py", "process"),
            naive=function_source(EXAMPLE / "grader/naive/test_hidden.py", "test_retry"),
            final=function_source(EXAMPLE / "grader/final/test_hidden_payments.py", "test_concurrent_duplicates_charge_once"),
        ),
    )
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fonts = font("Jost", "jost.woff2", "300 700") + font("JetBrains Mono", "jetbrains-mono.woff2", "400 700")
    html = (SITE / "template.html").read_text(encoding="utf-8")
    html = html.replace("/*__FONTS__*/", fonts).replace("/*__DATA__*/null", payload)
    out = SITE / "index.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=ROOT / "results/final/matrix.json")
    parser.add_argument("--repo-url", default="")
    args = parser.parse_args(argv)
    print(build(args.matrix, args.repo_url))


if __name__ == "__main__":
    main()
