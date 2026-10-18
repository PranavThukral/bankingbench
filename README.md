# Banking challenge pack — private draft

Synthetic payment and accounting tickets paired with naive and hardened behavioral graders.
The audit preserves plausible wrong solutions and tests structurally different valid solutions.
Publication and independent review are pending.

Python 3.12+ is required. Dependencies are exactly pinned in requirements.lock, a closed set checked by `python tools/check_lock.py`. The verified native environment uses Python 3.14 and PostgreSQL 16.13.

Native PowerShell:
```powershell
$env:PG_ADMIN_URL = 'postgresql://postgres@localhost:54329/postgres'
python -m pytest harness/tests -q
python -m harness.run_all --grader all
python -m harness.report --latest
```

Docker reproduction (written, not executed on the authoring machine):
```sh
docker compose up -d
make matrix
make export
make check
```
The disposable PostgreSQL data directory is tmpfs and fsync is off for speed. Never use this
configuration for real data. The internal compose network has no internet egress.

Every candidate runs in a fresh temporary workspace and, where required, fresh database.
`BCP_TMP` overrides the tempfile-based root (the image sets `/tmp/bcp`). Hidden tests live outside
the workspace. This is reproducibility isolation, not protection from hostile Python programs.
`results/LATEST` is a portable pointer file, never a symlink.

No remote, push or publication has been made. See GATES.md before publishing.

## Add a task
Follow [docs/TASK_FORMAT.md](docs/TASK_FORMAT.md). Write the ticket, a runnable starter in which the feature is genuinely
missing (200 to 600 lines of non-test code, `ref_diff_lines` at or above the difficulty floor), visible
regression, valid overlays and at least two realistic wrong overlays. Declare intended failing
tests and naive predictions in task.toml. Commit the naive grader, measure and log the gaps, then
write and commit the hardened grader. Run the full matrix, realism, leaks and distance checks.

## Results snapshot (results/final/)
Matrix produced from a clean tree at commit `1f1fa3e` (v2 starters, review R1 to R6 applied).

| Grader | Wrong solutions passed | Starters passed | Valid solutions rejected | Infra errors |
|---|---|---|---|---|
| naive | 20 / 30 | 1 / 10 | 0 / 20 | 0 |
| final | 0 / 30 | 0 / 10 | 0 / 20 | 0 |

- 10 tasks, 50 solution variants plus 10 starters, 120 runs (`--grader all`). Naive graders have 3 to 4 tests, final
  graders 6 to 18 (including generated cases).
- v1 numbers (superseded): naive graders let 29 of 30 wrong solutions and 5 of 10 starters through. The drop to 20 of 30 and
  1 of 10 comes from the v2 starters (the ticket's feature is now missing, not one line away) and from naive graders that
  include the ticket's worked example and a validation case; see [analysis/findings.md](analysis/findings.md) for each variant.
- Starter-to-reference diff (`ref_diff_lines`, changed lines over `.py` files): 01 41, 02 38, 03 25, 04 64, 05 52, 06 40,
  07 27, 08 42, 09 35, 10 63. Three wrong variants are regressive (they break a test the starter already passes) and carry
  a logged rationale: 01 `wrong_key_scope`, 02 `wrong_round_daily`, 07 `wrong_inclusive_2359`.
- **Measured wall-clock (native, not Docker):** 139.7 s for the committed clean `run_all --grader all` (4 workers, Windows 11,
  Python 3.14.7, PostgreSQL 16.13 local, fsync off). An earlier run took 223.6 s because task 05's valid solutions hit the
  old 90 s timeout; the limit is now 240 s (F-111). The Docker timing (S4) is unmeasured.
- `run_all --grader final --repeat 3`: 180/180 ok, 0 flips. Task 01 race test, 20 repeats x 3 variants: 60/60 ok, 0 flips.
- `export_harbor --validate`: reference reward 1 and starter reward 0 for all 10 tasks.
- Read [docs/SUMMARY.md](docs/SUMMARY.md) for the one-pager and [analysis/findings.md](analysis/findings.md) for the hardening log.
