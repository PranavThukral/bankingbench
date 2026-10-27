# BankingBench — one-page summary

## Problem
A coding task is only as good as its grader. A grader that accepts plausible-but-wrong code (a *false pass*) rewards
the wrong behaviour and inflates eval scores. A grader that rejects structurally different correct code (a *false
fail*) punishes valid solutions. Banking code is a good stress test: most bugs are invisible on ordinary inputs and
show up only at rounding ties, boundaries, concurrent retries or after a rejected operation.

## What was built
- **10 repository-style tasks**, all synthetic: idempotent payments (FastAPI + PostgreSQL), interest accrual, FX
  quotes, ledger reconciliation, a double-entry ledger (PostgreSQL), card holds, statement periods across time zones,
  refund limits, tiered fees and a fixed-width batch-file parser.
- Per task: a ticket, a runnable starter with the feature missing, a reference solution, a structurally different
  correct alternative, three plausible wrong solutions, and two graders: a **naive** one committed first and a
  **hardened** one.
- A harness that runs every solution and the unmodified starter against both graders, each in a fresh workspace and a
  fresh database with its own unprivileged role, and checks every verdict against the grader's expected test list.
- A **held-out set** of 52 solutions (44 wrong, 8 correct) written by an independent adversarial review, run with
  `python -m harness.heldout`.
- Export to the Harbor task format, the format Datacurve uses for its public DeepSWE benchmark
  ([source](https://hub.harborframework.com/datasets/datacurve/deep-swe)). A local oracle check scores the reference 1
  and the starter 0 on all 10 tasks.

## Headline numbers
| | Naive graders | Hardened graders |
|---|---|---|
| Authored wrong solutions accepted | 20 of 30 | 0 of 30 |
| Unmodified starters accepted | 1 of 10 | 0 of 10 |
| Correct solutions rejected | 0 of 20 | 0 of 20 |

**Independent check.** Before the held-out set was used, the hardened graders rejected only **6 of 44** independent
wrong solutions and accepted 6 of 8 independent correct ones. Nearly every miss broke a rule the ticket stated but no
test checked. Closing those gaps took 33 new or extended tests and three clarified ticket rules; the graders now reject
46 of 46 and accept 6 of 6. That second figure is no longer independent, because the graders were fixed against those
same solutions. The baseline is the honest measure of how far authored wrong solutions alone get you.

Full matrix: 120 runs in 80 s (4 workers), 0 infrastructure errors, identical on Python 3.14 and 3.12. Three repeats
gave 180/180 with no flips; the task 01 race test gave 60/60.

## Patterns (details in analysis/findings.md)
1. **Bugs that need two events.** Retry races, lost in-memory state, double reversals and expired holds pass any
   single-request test.
2. **Rounding ties and boundaries.** Half-up vs banker's rounding, float drift and off-by-one tier bounds agree with
   the right answer almost everywhere; they need searched inputs checked with exact arithmetic.
3. **Right totals, wrong pairing.** Reused ledger entries and currencies netted together give plausible counts.
4. **Stated but untested rules.** The biggest gap the held-out set found: graders hardened against the author's own
   wrong solutions still missed most rules nobody thought to break.

## Limitations
- All tasks and solutions are synthetic; no model has been run on the tasks yet.
- Blind reviews of the tickets are self-reviews; `check_done` reports them as SELF-REVIEW, not PASS.
- Solver code still runs as the same OS user as the grader. The harness now catches forged or incomplete results it can
  detect, but a candidate that forges a complete, consistent result from inside the test process is not stopped here;
  that needs separate containers ([docs/ISOLATION.md](ISOLATION.md)).
- Verified on Windows with PostgreSQL 16.13 under Python 3.14 and 3.12. The Docker path has not been timed.
- The v2 naive graders and their predictions were revised after the hardened graders existed, so only the v1 and v3
  predictions were recorded before the naive runs.
