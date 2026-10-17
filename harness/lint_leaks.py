import io
import re
import tokenize

from harness.discover import discover


def scan(task):
    hits = []
    for path in sorted((task.path / "starter").rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = str(path.relative_to(task.path / "starter")).replace("\\", "/")
        text = path.read_bytes().decode("utf-8", errors="replace")
        for term in task.leak_terms:
            if term.lower() in text.lower() and f"{relative}:{term}" not in task.leak_allow:
                hits.append(f"{relative}: forbidden term {term}")
        if path.suffix == ".py":
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type == tokenize.COMMENT and re.search(r"\b(bug|fix|trap|wrong|hint|race|todo)\b", token.string, re.I):
                    key = f"{relative}:{token.start[0]}"
                    if key not in task.leak_allow:
                        hits.append(f"{key}: revealing comment")
        reference = task.path / "solutions/reference" / relative
        if reference.is_file() and reference.read_bytes() == path.read_bytes():
            if f"{relative}:identical" not in task.leak_allow:
                hits.append(f"{relative}: identical reference overlay")
    return hits


def main():
    failures = []
    for task in discover():
        hits = scan(task)
        print(f"{task.id}: {'FAIL' if hits else 'PASS'}")
        failures += [f"{task.id}: {hit}" for hit in hits]
    print("\n".join(failures))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
