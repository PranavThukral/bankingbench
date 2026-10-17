"""Small authoring helpers; generated task files are the reviewable source of truth."""
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def write(path, text):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8", newline="\n")


def task_meta(slug, title, package, interface, wrongs, alternative, requires=(), terms=(), difficulty="medium"):
    base = Path("tasks") / slug
    q = json.dumps
    text = (f'id = {q(slug)}\ntitle = {q(title)}\nmandatory = {str(slug[:2] in {"01","02","04","05"}).lower()}\n'
            f'difficulty = {q(difficulty)}\ntags = {q([package, *requires])}\nrequires = {q(list(requires))}\n'
            f'timeout_seconds = 90\npublic_interface = {q(interface)}\nleak_terms = {q(list(terms))}\n'
            '[variants.reference]\nkind = "reference"\n[variants.alt_valid]\nkind = "alt_valid"\n'
            f'structural_difference = {q(alternative)}\n')
    for name, bug, tests in wrongs:
        text += (f'[variants.{name}]\nkind = "wrong"\nbug = {q(bug)}\n'
                 f'must_fail = {q(tests)}\npredicted_naive = "false_pass"\n')
    write(base / "task.toml", text)
    write(base / "starter" / package / "__init__.py", '"""Synthetic domain package."""\n')
    write(base / "starter/README.md", f"# {title}\n\nSynthetic training service. Python 3.12+. From this directory run `python -m pytest tests -q`.\nDependencies are provided by the pack runner. See ../PROBLEM.md for the ticket.\n")
    write(base / "grader/naive/conftest.py", 'pytest_plugins = ["graderlib.db"]\nimport graderlib.hypothesis_profiles  # noqa: F401\n')
    return base
