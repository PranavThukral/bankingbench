# Banking challenge pack — private draft

Synthetic payment and accounting tickets paired with naive and hardened behavioral graders.
The audit preserves plausible wrong solutions and tests structurally different valid solutions.
Publication and independent review are pending.

Python 3.12+ is required. Dependencies are exactly pinned in requirements.lock. The verified native environment uses Python 3.14 and PostgreSQL 16.13.

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
Follow [docs/TASK_FORMAT.md](docs/TASK_FORMAT.md). Write the ticket, a runnable starter with visible
regression, valid overlays and at least two realistic wrong overlays. Declare intended failing
tests and naive predictions in task.toml. Commit the naive grader, measure and log the gaps, then
write and commit the hardened grader. Run the full matrix, realism, leaks and distance checks.

## Results snapshot (results/final/)
| Grader | Wrong solutions passed | Starters passed | Valid solutions rejected | Infra errors |
|---|---|---|---|---|
| naive | 29 / 30 | 5 / 10 | 0 / 20 | 0 |
| final | 0 / 30 | 0 / 10 | 0 / 20 | 0 |

- 10 tasks, 50 solution variants plus 10 starters, 120 runs (`--grader all`).
- **Measured wall-clock (native, not Docker):** 152–174 s across two runs for `run_all --grader all` with 4 workers on
  Windows 11, Python 3.14.7, PostgreSQL 16.13 (local, fsync off). The Docker timing (S4) is unmeasured.
- `run_all --grader final --repeat 3`: 180/180 ok, 0 flips. Task 01 race test, 20 repeats × 3 variants: 0 flips.
- `export_harbor --validate`: reference reward 1 and starter reward 0 for all 10 tasks.
- Read [docs/SUMMARY.md](docs/SUMMARY.md) for the one-pager and [analysis/findings.md](analysis/findings.md) for the hardening log.
