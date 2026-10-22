import argparse
import json
from pathlib import Path
import re
import shutil

from harness import config
from harness.check_realism import ref_diff_lines, diff_floor
from harness.discover import discover
from harness.evidence import load, matches
from harness.lint_leaks import scan
from harness.run_all import latest


LOC_MIN, LOC_MAX = 200, 600


def package_loc(task):
    """Lines of non-test package code in starter/ (tests/ directories and conftest.py excluded)."""
    root = task.path / "starter"
    return sum(len(p.read_text(encoding="utf-8").splitlines()) for p in root.rglob("*.py")
               if "__pycache__" not in p.parts and "tests" not in p.relative_to(root).parts
               and p.name != "conftest.py")


def design_ok(realism, tasks):
    """S7 design half: diff floor recomputed from source, regression rationales from the receipt."""
    rows = {r["task"]: r for r in realism.get("design", [])}
    return bool(tasks) and all(
        t.id in rows and rows[t.id]["ok"] and ref_diff_lines(t) >= diff_floor(t) for t in tasks)


def repeat_ok(matrix, tasks, names, repeats):
    if not matrix or matrix.get("flips") or not matches(matrix, tasks):
        return False
    expected = {(t.id, v.name, rep) for t in tasks for v in t.variants
                if names is None or v.name in names for rep in range(repeats)}
    runs = [r for r in matrix["runs"] if r["grader"] == "final"]
    actual = {(r["task"], r["variant"], r["repeat"]) for r in runs}
    return expected <= actual and all(r["verdict"] == "ok" for r in runs)


def evaluate(metrics):
    """Pure criterion table; missing evidence is always a failure, never inferred success.

    A metric may also be the string "SELF-REVIEW": the evidence exists but was produced by the
    author, so it is reported as such (neither PASS nor FAIL, and not counted as a failure).
    """
    rows = []
    for criterion in range(1, 12):
        name = f"S{criterion}"
        value = metrics.get(name, False)
        if name == "S4" and not metrics.get("docker_available"):
            rows.append((name, "SKIP (no docker)"))
        elif value == "SELF-REVIEW":
            rows.append((name, "SELF-REVIEW"))
        else:
            rows.append((name, "PASS" if value else "FAIL"))
    return rows


def review_receipt(task, root=None):
    """True when reviews/<task>.md names a reviewer who is not the author (an independent review)."""
    path = (root or config.ROOT) / "reviews" / f"{task.id}.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    field = lambda key: (re.search(rf"^\W*{key}\W*:\s*(.+?)\s*$", text, re.I | re.M) or [None, ""])[1].strip(" *_`")  # noqa: E731
    reviewer, author = field("reviewer"), field("author")
    return bool(reviewer) and reviewer.lower() != author.lower() and reviewer.lower() not in {"tbd", "none", "n/a", "self"}


def notes_claim_review(task):
    text = (task.path / "NOTES.md").read_text(encoding="utf-8")
    return "## Blind review" in text and "No unresolved graded ambiguity" in text


def s5_status(tasks, root=None):
    """FAIL without the NOTES claim; PASS only with an independent receipt per task; else SELF-REVIEW."""
    if not tasks or not all(notes_claim_review(t) for t in tasks):
        return False
    return True if all(review_receipt(t, root) for t in tasks) else "SELF-REVIEW"


def heldout_ok(receipt, tasks):
    """S11: the held-out receipt covers the catalog, matches current sources, and every expectation holds."""
    if not receipt or receipt.get("source_changed_during_run") or not matches(receipt, tasks):
        return False
    root = config.ROOT / "heldout"
    try:
        catalog = (root / "catalog.toml")
        from harness.heldout import load_catalog, overlay_digests
        import hashlib
        rows = load_catalog(catalog)
        if receipt.get("catalog_digest") != hashlib.sha256(catalog.read_bytes()).hexdigest():
            return False
        if receipt.get("overlay_digests") != overlay_digests(rows, root):
            return False
    except (OSError, ValueError, KeyError):
        return False
    runs = receipt.get("runs", [])
    seen = {(r.get("task"), r.get("variant")) for r in runs}
    if seen != {(r["task"], r["name"]) for r in rows}:
        return False
    return all(r.get("verdict") == "ok" and
               r.get("outcome") == ("FAIL" if r.get("expect") == "reject" else "PASS") for r in runs)


def collect(tasks, matrix, evidence, docker_available):
    runs = matrix.get("runs", [])
    final = {(r["task"], r["variant"]): r for r in runs if r["grader"] == "final" and r["repeat"] == 0}
    naive = {(r["task"], r["variant"]): r for r in runs if r["grader"] == "naive" and r["repeat"] == 0}
    expected = {(t.id, v.name) for t in tasks for v in t.variants}
    wrong = {(t.id, v.name) for t in tasks for v in t.variants if v.kind == "wrong"}
    corrected = sum(r["verdict"] == "false_pass" and key in final and final[key]["verdict"] == "ok"
                    for key, r in naive.items() if key in wrong)
    realism, oracle = evidence.get("realism", {}), evidence.get("oracle", {})
    realism_rows = realism.get("rows", [])
    oracle_rows = oracle.get("rows", [])
    metrics = dict(
        S1=len(tasks) >= 8 and {"01", "02", "04", "05"} <= {t.id[:2] for t in tasks} and all(
            {"reference", "alt_valid"} <= {v.kind for v in t.variants} and
            sum(v.kind == "wrong" for v in t.variants) >= 2 and
            all((t.path / "grader" / g).is_dir() for g in ("naive", "final")) and
            all((t.path / "solutions" / v.name).is_dir() for v in t.variants if v.name != "starter") and
            LOC_MIN <= package_loc(t) <= LOC_MAX for t in tasks),
        S2=bool(expected) and expected <= final.keys() and matches(matrix, tasks) and not matrix.get("source_changed_during_run") and
            all(r["verdict"] == "ok" for r in final.values()),
        S3=corrected >= 3,
        S4=evidence.get("docker_wall_s", float("inf")) < 300,
        S5=s5_status(tasks),
        S6=bool(wrong) and all(k in final and final[k]["outcome"] == "FAIL" and final[k]["must_fail_hit"] for k in wrong),
        S7=matches(realism, tasks) and expected <= {(r["task"], r["variant"]) for r in realism_rows} and
            all(r["ok"] for r in realism_rows) and design_ok(realism, tasks) and
            realism.get("py312_lint", {}).get("ok") is True,
        S8=repeat_ok(evidence.get("repeat"), tasks, None, 3) and
            repeat_ok(evidence.get("flake"), [t for t in tasks if t.id[:2] == "01"],
                      {"reference", "alt_valid", "wrong_retry_race"}, 20),
        S9=bool(tasks) and all(not scan(t) for t in tasks),
        S10=matches(oracle, tasks) and {t.id for t in tasks} <= {r["task"] for r in oracle_rows} and
             all(r["reference_reward"] == 1 and r["starter_reward"] == 0 for r in oracle_rows),
        S11=heldout_ok(evidence.get("heldout"), tasks),
        docker_available=docker_available,
    )
    return metrics


def gather(tasks, heldout_path=None):
    evidence = load(config.RESULTS / "final/verification.json", {})
    evidence["realism"] = load(config.RESULTS / "realism.json", evidence.get("realism", {}))
    evidence["oracle"] = load(config.RESULTS / "oracle.json", evidence.get("oracle", {}))
    evidence["heldout"] = load(heldout_path or config.RESULTS / "final/heldout.json", {})
    for path in sorted(config.RESULTS.rglob("matrix.json")):
        matrix = load(path, {})
        invocation = matrix.get("invocation", {})
        if invocation.get("repeat", 0) >= 3 and invocation.get("tasks") is None and matches(matrix, tasks):
            evidence["repeat"] = matrix
        one = [t for t in tasks if t.id[:2] == "01"]
        if invocation.get("repeat", 0) >= 20 and invocation.get("tasks") == "01" and matches(matrix, one):
            evidence["flake"] = matrix
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="source", type=Path,
                        help="matrix.json to evaluate (default: results/final/matrix.json, else the latest run)")
    parser.add_argument("--heldout", type=Path,
                        help="held-out receipt for S11 (default: results/final/heldout.json)")
    parser.add_argument("--save-evidence", action="store_true",
                        help="write the gathered evidence to results/final/verification.json")
    args = parser.parse_args(argv)
    tasks = discover()
    source = args.source or (config.RESULTS / "final/matrix.json")
    if not source.exists():
        source = latest()
    matrix = load(source, {})
    evidence = gather(tasks, args.heldout)
    if args.save_evidence:
        out = config.RESULTS / "final/verification.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({k: v for k, v in evidence.items() if k != "heldout"}, indent=2) + "\n", encoding="utf-8")
    rows = evaluate(collect(tasks, matrix, evidence, shutil.which("docker") is not None))
    print("Criterion | Status\n----------|-----------------")
    for name, status in rows:
        print(f"{name:<9} | {status}")
    return int(any(status == "FAIL" for _, status in rows))


if __name__ == "__main__":
    raise SystemExit(main())
