# Banking challenge pack — private draft

Synthetic payment and accounting tickets paired with naive and hardened behavioral graders.
The audit preserves plausible wrong solutions and tests structurally different valid solutions.
Publication and independent review are pending.

Python 3.12+ is required. Dependencies are exactly pinned in requirements.lock; no installation
was performed during authoring. The verified native environment uses Python 3.14 and PostgreSQL 16.13.

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

No remote, push or publication has been made. Review and transfer this history before publishing.

## Add a task
Follow [docs/TASK_FORMAT.md](docs/TASK_FORMAT.md). Write the ticket, a runnable starter with visible
regression, valid overlays and at least two realistic wrong overlays. Declare intended failing
tests and naive predictions in task.toml. Commit the naive grader, measure and log the gaps, then
write and commit the hardened grader. Run the full matrix, realism, leaks and distance checks.

Results and measured timing are filled from the final committed snapshot after verification.
