# Task authoring contract

## 6. Task authoring contract

### 6.1 Per-task layout
```
tasks/01_idempotent_payments/
├── task.toml
├── PROBLEM.md            # the ticket given to the model (becomes Harbor instruction.md)
├── NOTES.md              # reviewer-only: traps, why each wrong is wrong, grader design, flake data
├── starter/              # the repo the model receives
│   ├── README.md         # how to run visible tests
│   ├── <package>/...
│   └── tests/            # VISIBLE tests: happy path + ≥1 failing test that shows the ticket
├── solutions/
│   ├── reference/        # overlay
│   ├── alt_valid/        # overlay, structurally different
│   └── wrong_<slug>/     # 2–3 overlays
└── grader/
    ├── naive/            # v0: written first, committed first
    │   ├── conftest.py
    │   └── test_hidden.py
    └── final/            # hardened
        ├── conftest.py
        └── test_hidden_*.py
```

### 6.2 `task.toml` schema (validated by `discover.py`; reject unknown keys)
```toml
id            = "01_idempotent_payments"        # must equal the dir name
title         = "Make payment creation idempotent"
mandatory     = true
difficulty    = "hard"                            # easy | medium | hard
tags          = ["concurrency", "postgres", "http"]
requires      = ["postgres"]                      # [] or ["postgres"]
timeout_seconds = 90                              # per run; default 60
public_interface = [                               # what graders may touch; nothing else
  "app.main:create_app(database_url: str, gateway: Gateway) -> FastAPI",
  "app.gateway:Gateway (Protocol)",
  "HTTP POST /v1/payments",
]
leak_terms    = ["ON CONFLICT", "advisory", "FOR UPDATE", "idempotency_keys"]  # case-insensitive, scanned in starter/

[variants.reference]
kind = "reference"

[variants.alt_valid]
kind = "alt_valid"
structural_difference = "Serializes duplicates with pg_advisory_xact_lock and waits; reference reserves a key row and returns 409 while in flight."

[variants.wrong_retry_race]
kind = "wrong"
bug  = "Check-then-insert: SELECT for existing key, call gateway, INSERT. Concurrent duplicates both charge."
must_fail = ["test_concurrent_duplicates_charge_once"]
predicted_naive = "false_pass"                    # prediction recorded before running naive grader
# regression_rationale = "..."                   # required only if the starter already passes a must_fail test
```
Expected outcome comes from `kind`: `reference` and `alt_valid` → PASS, `wrong` → FAIL. The
implicit variant `starter` (no overlay) is always run and expected to FAIL under `final`. This
guards against tasks that are solved by doing nothing.

### 6.3 Authoring rules
- **PROBLEM.md** reads like a real ticket: context, required behavior, explicit rules (rounding
  mode, currency minor units, timezone, error codes), the public interface, and "how to run tests".
  It must state every rule a grader checks. It must not hint at the trap ("be careful of races"
  is a leak; "concurrent duplicate requests must result in a single charge" is a requirement).
- **Starter** is 200–600 LOC of non-test package code (tests and conftest.py are not counted): a runnable, idiomatic
  repository in which the ticket's feature is genuinely missing, with supporting code (models, I/O, CLI, storage) that is
  not the answer. `check_realism` requires `ref_diff_lines` (changed lines from starter to reference over `.py` files) of at
  least 40 for hard, 25 for medium and 12 for easy tasks, and requires a `regression_rationale` (repeated in NOTES.md) for
  every wrong variant whose declared `must_fail` tests the starter already passes.
  No `TODO` comments that name the fix. No dead code that contains the answer.
- **Visible tests** (`starter/tests/`) pass the happy path and include ≥ 1 test the starter fails,
  so the ticket is observable. **Every wrong variant must pass all visible tests** (this is
  the realism bar, S7).
- **Graders** import only names listed in `public_interface`. They assert behavior: HTTP
  status/body, return values, DB-observable state through the public API. They never assert
  on function names, SQL text, internal tables or log output.
- **Wrong variants** are bugs a competent engineer or model could plausibly write. Prefer
  "reference + one realistic defect" or an independent implementation with one realistic flaw.
  No syntax errors, no missing functions, no `raise NotImplementedError`.
- **alt_valid** must differ in algorithm or data flow, not just in variable names. `alt_distance`
  must report a difflib ratio vs the reference of < 0.6 over changed files (warn at ≥ 0.6, which
  the author must acknowledge).

---

