"""Build the landing page and task pages from repository evidence and sectioned site copy.

Usage: python site/build.py [--matrix results/final/matrix.json] [--repo-url https://github.com/...]
Landing-page figures are computed in the browser; task-page grids are computed at build time.
Code excerpts, tickets, metadata and results are read from the repository.
"""
import argparse
import ast
from html import escape
import json
from pathlib import Path
import re
import shutil
import tomllib
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
FONTS = ROOT / "harness/templates/fonts"
EXAMPLE = ROOT / "tasks/01_idempotent_payments"
RUN_FIELDS = ("task", "variant", "kind", "grader", "verdict", "outcome", "tests", "failed_tests",
              "must_fail_hit", "duration_s", "predicted_naive", "stderr_tail")


def inject_copy(template, content):
    """Only plain, escaped text is allowed in copy slots, including attributes."""
    return re.sub(r"\{\{(\w+)\.(\w+)\}\}",
                  lambda m: escape(content[m[1]][m[2]]), template)


def script_json(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))


def inline_markdown(text):
    """Render a small inline grammar; raw HTML and unsafe link schemes stay text."""
    pattern = (r"`([^`]+)`|\[([^\]\n]+)\]\(([^\s)]+)\)|\*\*(.+?)\*\*|(?<!\w)__(.+?)__(?!\w)"
               r"|\*([^*]+)\*|(?<!\w)_([^_]+)_(?!\w)")
    out, end = [], 0
    for match in re.finditer(pattern, text):
        out.append(escape(text[end:match.start()]))
        code, label, href, bold, under_bold, italic, under_italic = match.groups()
        if code is not None:
            out.append(f"<code>{escape(code)}</code>")
        elif label is not None:
            scheme = urlsplit(href).scheme.lower()
            if scheme in ("", "http", "https", "mailto") and not href.startswith("//"):
                out.append(f'<a href="{escape(href)}">{inline_markdown(label)}</a>')
            else:
                out.append(escape(match[0]))
        elif bold is not None or under_bold is not None:
            out.append(f"<strong>{inline_markdown(bold or under_bold)}</strong>")
        else:
            out.append(f"<em>{inline_markdown(italic or under_italic)}</em>")
        end = match.end()
    out.append(escape(text[end:]))
    return "".join(out)


def markdown(text):
    """Dependency-free ticket renderer: blocks, lists, fences and escaped inline markup."""
    out, paragraph, items = [], [], []
    list_kind, fence, code = None, None, []

    def flush():
        nonlocal list_kind
        if paragraph:
            out.append(f'<p>{inline_markdown(" ".join(paragraph))}</p>')
            paragraph.clear()
        if items:
            out.append(f'<{list_kind}>' + "".join(f'<li>{inline_markdown(x)}</li>' for x in items) + f'</{list_kind}>')
            items.clear()
            list_kind = None

    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                out.append('<pre tabindex="0"><code>' + escape("\n".join(code)) + '</code></pre>')
                fence, code = None, []
            else:
                code.append(line)
            continue
        if marker:
            flush()
            fence = marker[1]
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        item = re.match(r"^\s*(?:([-+*])|\d+[.)])\s+(.+)$", line)
        if not line.strip():
            flush()
        elif heading:
            flush()
            # The page owns h1; ticket headings start at h3.
            level = min(6, len(heading[1]) + 2)
            out.append(f'<h{level}>{inline_markdown(heading[2])}</h{level}>')
        elif item:
            kind = "ul" if item[1] else "ol"
            if paragraph or (list_kind and kind != list_kind):
                flush()
            list_kind = kind
            items.append(item[2])
        elif items and line.startswith(("  ", "\t")):
            items[-1] += " " + line.strip()
        else:
            if items:
                flush()
            paragraph.append(line.strip())
    if fence:
        out.append('<pre tabindex="0"><code>' + escape("\n".join(code)) + '</code></pre>')
    flush()
    return "\n".join(out)


def hidden_tests(task, grader):
    """Parse test functions and Hypothesis-generated TestCase classes without importing tests."""
    tests = []
    for path in sorted((ROOT / "tasks" / task / "grader" / grader).glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                tests.append((path.stem, node.name))
            elif (isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute)
                  and node.value.attr == "TestCase"):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.startswith("Test"):
                        tests.append((f"{path.stem}.{target.id}", "runTest"))
    return tests


def test_grid(task, grader, variants, index, content):
    labels = content["task_page"]
    tests = hidden_tests(task, grader)
    headers = "".join(f'<th scope="col">{escape(labels.get(v, v.removeprefix("wrong_").replace("_", " ")))}</th>'
                      for v in variants)
    rows = []
    for module, name in tests:
        cells = []
        for variant in variants:
            run = index.get((task, variant, grader))
            declared = name in variants[variant].get("must_fail", [])
            failed = [x.replace("\\", "/").split("::") for x in (run or {}).get("failed_tests", [])]
            is_failed = any(parts[0].removesuffix(".py").split("/")[-1] == module and
                            parts[-1].split("[")[0] == name for parts in failed)
            # Never turn an absent or incomplete run into a green cell.
            recorded = (run and run["tests"]["total"] > 0 and run.get("outcome") != "ERROR"
                        and not run["tests"].get("errors") and not run["tests"].get("skipped"))
            state = "fail" if is_failed else "pass" if recorded else "unknown"
            mark = f' <abbr title="{escape(labels["must_fail"])}">*</abbr>' if declared else ""
            cells.append(f'<td class="test-{state}">{escape(labels[state])}{mark}</td>')
        if name == "runTest":
            subject = re.sub(r"(?<!^)(?=[A-Z])", " ", module.split(".")[-1].removeprefix("Test"))
            human = labels["state_machine"].format(name=subject)
        else:
            human = name.removeprefix("test_").replace("_", " ").capitalize()
        rows.append(f'<tr><th scope="row" title="{escape(module + "::" + name)}">{escape(human)}</th>{"".join(cells)}</tr>')
    label = escape(labels["scroll_grid"].format(grader=labels[grader]))
    sample = index.get((task, "reference", grader))
    total = sample["tests"]["total"] if sample else 0
    return (f'<div class="test-scroll" tabindex="0" role="region" aria-label="{label}"><table class="test-grid">'
            f'<caption>{escape(labels[grader])} · {escape(labels["test_count"].format(total=total, rows=len(tests)))}</caption>'
            f'<thead><tr><th scope="col">{escape(labels["test"])}</th>{headers}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def task_pages(task_data, runs, content):
    index = {(r["task"], r["variant"], r["grader"]): r for r in runs}
    template = inject_copy((SITE / "task-template.html").read_text(encoding="utf-8"), content)
    labels = content["task_page"]
    ids = list(task_data)
    (SITE / "tasks").mkdir(exist_ok=True)
    for position, (task, meta) in enumerate(task_data.items()):
        variants = {"starter": {}, **meta["variants"]}
        variants = {v: variants[v] for v in ("starter", "reference", "alt_valid", *sorted(v for v in variants if v.startswith("wrong_")))}
        solutions = []
        for variant, spec in variants.items():
            if variant == "starter":
                continue
            result = []
            for grader in ("naive", "final"):
                run = index.get((task, variant, grader))
                state = "accepted" if run and run["outcome"] == "PASS" else "rejected" if run and run["outcome"] == "FAIL" else "error"
                text = (labels["result"].format(grader=labels[grader], outcome=content["common"][state],
                                               passed=run["tests"]["passed"], total=run["tests"]["total"])
                        if run else labels["not_run"].format(grader=labels[grader]))
                result.append(f'<span class="tag {"good" if state == "accepted" else "bad"}">{escape(text)}</span>')
            name = labels.get(variant, variant.removeprefix("wrong_").replace("_", " ").capitalize())
            note = spec.get("bug") or spec.get("structural_difference") or labels["reference_note"]
            solutions.append(f'<article class="solution"><h3>{escape(name)}</h3><code>{escape(variant)}</code>'
                             f'<p>{escape(note)}</p><div class="tags">{"".join(result)}</div></article>')
        neighbours = []
        for offset, key in ((-1, "previous"), (1, "next")):
            if 0 <= position + offset < len(ids):
                target = ids[position + offset]
                neighbours.append(f'<a href="{target}.html">{escape(labels[key])}<span>{escape(target[:2])} · {escape(task_data[target]["title"])}</span></a>')
        sources = (("PROBLEM.md", "ticket_source"), ("starter/", "starter_source"), ("solutions/", "solutions_source"),
                   ("grader/naive/", "naive_source"), ("grader/final/", "final_source"), ("task.toml", "metadata_source"))
        values = dict(title=escape(meta["title"]), page_title=escape(labels["title"].format(title=meta["title"])),
                      number=escape(task[:2]), area=escape(meta["area"]), stack=escape(meta["stack"]),
                      difficulty=escape(meta["difficulty"]), summary=escape(meta["summary"]),
                      checks="".join(f'<li>{escape(check)}</li>' for check in meta["checks"]),
                      solutions="".join(solutions), navigation="".join(neighbours),
                      final_grid=test_grid(task, "final", variants, index, content),
                      naive_grid=test_grid(task, "naive", variants, index, content),
                      ticket=markdown((ROOT / "tasks" / task / "PROBLEM.md").read_text(encoding="utf-8")),
                      sources="".join(f'<a href="../../tasks/{task}/{path}">{escape(labels[key])}</a>' for path, key in sources))
        html = re.sub(r"<!--__(\w+)__-->", lambda m: values[m[1]], template)
        (SITE / "tasks" / f"{task}.html").write_text(html, encoding="utf-8", newline="\n")


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
    catalog = tomllib.loads((ROOT / "tasks/catalog.toml").read_text(encoding="utf-8"))
    for path in sorted((ROOT / "tasks").iterdir()):
        if not (path / "task.toml").exists():
            continue
        meta = tomllib.loads((path / "task.toml").read_text(encoding="utf-8"))
        rows[meta["id"]] = dict(
            title=meta["title"], difficulty=meta["difficulty"], tags=meta.get("tags", []),
            **catalog[meta["id"]],
            variants={name: {k: v for k, v in spec.items() if k in ("kind", "bug", "structural_difference", "must_fail")}
                      for name, spec in meta.get("variants", {}).items()})
    return rows


def build(matrix_path, repo_url):
    content = tomllib.loads((SITE / "content.toml").read_text(encoding="utf-8"))
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
    for filename in ("jost.woff2", "jetbrains-mono.woff2"):
        shutil.copyfile(FONTS / filename, SITE / "assets" / filename)
    html = inject_copy((SITE / "template.html").read_text(encoding="utf-8"), content)
    items = []
    for task, meta in data["tasks"].items():
        items.append(f'<li><a href="tasks/{task}.html"><span class="task-number">{task[:2]}</span>'
                     f'<div><span class="task-area">{escape(meta["area"])}</span><h3>{escape(meta["title"])}</h3>'
                     f'<p>{escape(meta["summary"])}</p><div class="tags"><span class="tag">{escape(meta["stack"])}</span>'
                     f'<span class="tag">{escape(meta["difficulty"])}</span></div></div></a></li>')
    html = html.replace("<!--__TASK_LIST__-->", "".join(items))
    html = html.replace("/*__DATA__*/null", script_json(data)).replace("/*__COPY__*/null", script_json(content))
    task_pages(data["tasks"], runs, content)
    out = SITE / "index.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    if repo_url:
        for page in [out, *sorted((SITE / "tasks").glob("*.html"))]:
            page.write_text(link_to_repo(page.read_text(encoding="utf-8"), page.parent, repo_url),
                            encoding="utf-8", newline="\n")
    return out


# Served as web pages wherever the site is hosted; every other repository path links to GitHub instead.
HOSTED = ("site/", "results/final/report.html", "results/final/matrix.json")


def link_to_repo(html, page_dir, repo_url):
    """Point relative links that leave site/ (Markdown, source folders) at the repository on GitHub."""
    base = repo_url.rstrip("/")

    def swap(match):
        href = match[1]
        target = (page_dir / href.split("#")[0]).resolve()
        try:
            path = target.relative_to(ROOT).as_posix()
        except ValueError:
            return match[0]
        if path.startswith(HOSTED):
            return match[0]
        kind = "tree" if href.split("#")[0].endswith("/") or target.is_dir() else "blob"
        anchor = "#" + href.split("#", 1)[1] if "#" in href else ""
        return f'href="{base}/{kind}/main/{path}{anchor}"'

    return re.sub(r'href="((?:\.\./)+[^"]*)"', swap, html)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=ROOT / "results/final/matrix.json")
    parser.add_argument("--repo-url", default="")
    args = parser.parse_args(argv)
    print(build(args.matrix, args.repo_url))


if __name__ == "__main__":
    main()
