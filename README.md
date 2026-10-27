# BankingBench

Ten synthetic banking coding tasks, each graded twice: by a first-draft ("naive") grader written first, and by a hardened grader written after measuring what the first one missed. Every task ships with a reference solution, a structurally different correct solution and three plausible wrong ones, so you can see exactly which bugs each grader lets through.

**[Website](https://bankingbench.vercel.app)** · **[Results report](https://bankingbench.vercel.app/results/final/report.html)** · **[Hardening log](analysis/findings.md)** · **[One-page summary](docs/SUMMARY.md)**

## Results

| | Naive graders | Hardened graders |
|---|---|---|
| Wrong solutions accepted | 20 / 30 | 0 / 30 |
| Unmodified starters accepted | 1 / 10 | 0 / 10 |
| Correct solutions rejected | 0 / 20 | 0 / 20 |

**Independent check:** before tightening, the hardened graders rejected only 6 of 44 wrong solutions written by an independent review; after closing the gaps they exposed, 46 of 46 (see [heldout/](heldout/catalog.toml)). Identical on Python 3.14 and 3.12, repeated 3 times with no flips; the task 01 concurrency test ran 60 times with no flips. Every task exports to the [Harbor](https://docs.harborframework.com/tasks/overview) task format, and a local oracle check scores the reference 1 and the untouched starter 0.

## The tasks

| # | Area | The task |
|---|---|---|
| [01](tasks/01_idempotent_payments/PROBLEM.md) | Payments API | A payment endpoint must charge a card once per Idempotency-Key, no matter how the client retries. |
| [02](tasks/02_interest_accrual/PROBLEM.md) | Interest | Accrue daily interest on a CAD balance and post it at month ends, using Actual/365 and banker's rounding. |
| [03](tasks/03_fx_quotes/PROBLEM.md) | FX transfers | Quote a currency transfer with the fee taken in the source currency and each currency's own decimal places. |
| [04](tasks/04_ledger_reconciliation/PROBLEM.md) | Reconciliation | Match bank statement lines to ledger entries with exact, split, refund and duplicate rules, deterministically. |
| [05](tasks/05_double_entry/PROBLEM.md) | Ledger | Run a double-entry journal where every post balances per currency and is all-or-nothing. |
| [06](tasks/06_available_balance/PROBLEM.md) | Card holds | Compute available balance as posted funds minus active card holds, with capture, void and expiry. |
| [07](tasks/07_statement_periods/PROBLEM.md) | Statements | Select a month's transactions using midnight in the account's own time zone, converted to UTC. |
| [08](tasks/08_refund_limits/PROBLEM.md) | Refunds | Allow partial refunds up to the captured amount, which may be less than what was authorized. |
| [09](tasks/09_tiered_fees/PROBLEM.md) | Fees | Price a payment at one tier selected by an inclusive upper bound, then round and clamp the fee. |
| [10](tasks/10_batch_parser/PROBLEM.md) | Batch files | Validate an invented 80-character fixed-width payment file and reject the whole batch on any error. |

Each task lives in `tasks/<id>/`: `PROBLEM.md` (the ticket), `starter/` (the repo a solver receives), `solutions/` (reference, alternative and wrong variants as overlays on the starter), and `grader/naive` and `grader/final` (hidden tests). What each hardened grader checks is in [tasks/catalog.toml](tasks/catalog.toml).

## Run it

Needs Python 3.12+ and PostgreSQL 16 (tasks 01 and 05 use it).

```sh
pip install --no-deps -r requirements.lock
export PG_ADMIN_URL=postgresql://postgres:<password>@localhost:5432/postgres   # any superuser URL on a disposable server

python -m harness.run_all --grader all     # every solution against both graders → results/<stamp>/matrix.json
python -m harness.report --latest          # offline HTML report next to it
python -m harness.check_done               # the completion criteria in BLUEPRINT.md §1.1
```

Or with Docker: `docker compose up -d && make matrix` (written to spec but not yet timed). Each run gets a fresh workspace, a fresh database with its own unprivileged role, and an allow-listed environment; verdicts are checked against the grader's expected test list ([docs/ISOLATION.md](docs/ISOLATION.md)).

Other checks: `python -m harness.heldout` (the 52 independent solutions), `python -m harness.check_realism` (wrong solutions compile, lint clean and pass the visible tests), `python -m harness.lint_leaks` (no answer hints in starters), `python -m harness.export_harbor --validate` (Harbor export plus oracle check), `python site/build.py` (rebuild the website).

## How it was built

[BLUEPRINT.md](BLUEPRINT.md) is the spec. For each task the naive grader was committed before the hardened one, and every miss is logged with its commit in [analysis/findings.md](analysis/findings.md). The pack went through three rounds: v1, then a [review](docs/REVIEW-2026-10-17.md) that rebuilt starters which were one line away from the answer, then v3, which replaced three wrong solutions that broke behaviour the starter already got right. [docs/TASK_FORMAT.md](docs/TASK_FORMAT.md) describes how to add a task.

## Limitations

- All tasks and solutions are author-written and synthetic. No real bank, customer or system is represented, and no model has been run on the tasks yet.
- "0 of 30" and "46 of 46" are measured against solutions the graders were hardened on. The independent figure is the baseline: 6 of 44 before the held-out set was used.
- Solver code runs as the same OS user as the grader. Forged or incomplete results that the harness can cross-check are rejected, but a complete forgery from inside the test process needs container isolation to stop ([docs/ISOLATION.md](docs/ISOLATION.md)).
- Ticket blind reviews are self-reviews so far. Verified on Windows with PostgreSQL 16.13 under Python 3.14 and 3.12; the Docker path has not been timed.

MIT licensed.
