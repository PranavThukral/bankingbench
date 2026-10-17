from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Variant:
    name: str
    kind: str
    must_fail: tuple[str, ...] = ()
    bug: str = ""
    predicted_naive: str = ""
    structural_difference: str = ""

    @property
    def expected(self):
        return "PASS" if self.kind in {"reference", "alt_valid"} else "FAIL"


@dataclass(frozen=True)
class Task:
    path: Path
    id: str
    title: str
    mandatory: bool
    difficulty: str
    tags: tuple[str, ...]
    requires: tuple[str, ...]
    public_interface: tuple[str, ...]
    leak_terms: tuple[str, ...]
    variants: tuple[Variant, ...]
    timeout_seconds: float = 60
    leak_allow: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RunSpec:
    task: Task
    variant: Variant
    grader: str
    repeat: int = 0
    keep_workspaces: bool = False


@dataclass
class RunResult:
    task: str
    variant: str
    kind: str
    grader: str
    repeat: int
    expected: str
    outcome: str
    verdict: str
    tests: dict[str, int]
    failed_tests: list[str]
    must_fail_hit: list[str]
    duration_s: float
    stderr_tail: str = ""
    predicted_naive: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
