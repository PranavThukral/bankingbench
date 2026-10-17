from pathlib import Path
import re
import tomllib

from harness.config import TASKS
from harness.model import Task, Variant

KEYS = {"id", "title", "mandatory", "difficulty", "tags", "requires", "timeout_seconds",
        "public_interface", "leak_terms", "variants", "leak_allow"}
VKEYS = {"kind", "must_fail", "bug", "predicted_naive", "structural_difference"}


def load_task(path: Path) -> Task:
    data = tomllib.loads((path / "task.toml").read_text(encoding="utf-8"))
    if data.keys() - KEYS:
        raise ValueError(f"unknown task keys: {data.keys() - KEYS}")
    required = KEYS - {"timeout_seconds", "leak_allow"}
    if required - data.keys():
        raise ValueError(f"missing keys: {required - data.keys()}")
    if data["id"] != path.name or not re.fullmatch(r"[a-z0-9_]+", data["id"]):
        raise ValueError("id must equal directory name and be a safe identifier")
    if data["difficulty"] not in {"easy", "medium", "hard"}:
        raise ValueError("invalid difficulty")
    if data["requires"] not in ([], ["postgres"]):
        raise ValueError("invalid requires")
    if type(data["mandatory"]) is not bool:
        raise ValueError("mandatory must be boolean")
    for key in ("tags", "requires", "public_interface", "leak_terms"):
        if not isinstance(data[key], list) or not all(isinstance(x, str) for x in data[key]):
            raise ValueError(f"{key} must be a string array")
    timeout = data.get("timeout_seconds", 60)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be positive")
    variants = [Variant("starter", "starter")]
    for name, item in data["variants"].items():
        if not re.fullmatch(r"[a-z0-9_]+", name) or name == "starter":
            raise ValueError("invalid variant name")
        if item.keys() - VKEYS or item.get("kind") not in {"reference", "alt_valid", "wrong"}:
            raise ValueError("invalid variant schema")
        if item["kind"] == "wrong":
            if not item.get("must_fail") or not item.get("bug"):
                raise ValueError("wrong requires bug and nonempty must_fail")
            if item.get("predicted_naive") not in {"ok", "false_pass", "ok_wrong_reason", "infra_error"}:
                raise ValueError("wrong requires predicted_naive")
        if item["kind"] == "alt_valid" and not item.get("structural_difference"):
            raise ValueError("alt requires structural_difference")
        if not isinstance(item.get("must_fail", []), list):
            raise ValueError("must_fail must be an array")
        variants.append(Variant(name=name, **{**item, "must_fail": tuple(item.get("must_fail", []))}))
    allow = data.get("leak_allow", {})
    if not all(isinstance(v, str) and v.strip() for v in allow.values()):
        raise ValueError("leak exceptions require reasons")
    return Task(path.resolve(), data["id"], data["title"], data["mandatory"], data["difficulty"],
                tuple(data["tags"]), tuple(data["requires"]), tuple(data["public_interface"]),
                tuple(data["leak_terms"]), tuple(variants), timeout, allow)


def discover(root=TASKS, selected=None):
    found = [load_task(p.parent) for p in sorted(Path(root).glob("*/task.toml"))]
    if selected:
        wanted = set(selected.split(","))
        found = [t for t in found if t.id in wanted or t.id[:2] in wanted]
        matched = {v for v in wanted if any(t.id == v or t.id[:2] == v for t in found)}
        if wanted - matched:
            raise ValueError(f"unknown tasks: {wanted - matched}")
    return found
