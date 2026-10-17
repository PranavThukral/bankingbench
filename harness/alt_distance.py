import difflib
from harness.discover import discover


def distance(task):
    ref, alt = task.path / "solutions/reference", task.path / "solutions/alt_valid"
    files = sorted({p.relative_to(root) for root in (ref, alt) for p in root.rglob("*.py")})
    def contents(root):
        return "\n".join((root / p).read_text(encoding="utf-8") if (root / p).exists() else "" for p in files)
    return difflib.SequenceMatcher(None, contents(ref), contents(alt), autojunk=False).ratio()


def main():
    warnings = []
    for task in discover():
        ratio = distance(task)
        print(f"{task.id}: {ratio:.3f} {'WARN (author acknowledgement owed)' if ratio >= .6 else 'PASS'}")
        if ratio >= .6:
            warnings.append(task.id)
    return int(bool(warnings))


if __name__ == "__main__":
    raise SystemExit(main())
