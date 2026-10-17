# Banking challenge pack — one-page summary (private draft)

## Problem
A coding task is only as good as its grader. A grader that accepts plausible-but-wrong code
(a *false pass*) teaches a model the wrong thing and inflates eval scores. A grader that rejects
structurally different correct code (a *false fail*) punishes valid solutions. Banking and
payments code is a good stress test: most bugs are invisible on ordinary inputs and show up
only at rounding ties, boundaries, concurrent retries or after a rejected operation.

## What was built
- **10 repository-style tasks**, all synthetic: idempotent payments (FastAPI + PostgreSQL),
  interest accrual, FX quotes, ledger reconciliation, double-entry ledger (PostgreSQL),
  holds and available balance, statement periods across time zones, refund limits, tiered fees,
  and a fixed-width batch-file parser.
- Per task: a ticket (PROBLEM.md), a runnable starter with visible tests, a reference solution,
  a structurally different valid alternative, 3 realistic wrong solutions, and two graders:
  **naive** (written first and committed first) and **final** (hardened).
- A harness that runs every solution (plus the unmodified starter) against both graders in
  isolated workspaces and fresh databases, and produces `matrix.json` plus an offline HTML report.
- Quality gates: wrong solutions must compile, lint clean and pass the visible tests (realism);
  each must fail its *declared* hidden test (right reason); answer-leak scan on starters;
  similarity check between reference and alternative; 3× repeat and 20× concurrency flake runs.
- Export to the **Harbor** task format (`instruction.md`, `task.toml`, `environment/`,
  `tests/test.sh`, `solution/solve.sh`), with a local oracle check: reference scores 1 and
  starter scores 0 for all 10 tasks.

## Headline numbers (results/final/matrix.json)
| | Naive graders | Final graders |
|---|---|---|
| Wrong solutions passed (false pass) | **29 of 30** | **0 of 30** |
| Unmodified starters passed | 5 of 10 | 0 of 10 |
| Valid solutions rejected (false fail) | 0 of 20 | 0 of 20 |
| Hidden tests per task | 1–3 | 5–12 |

Full matrix: 120 runs in 152 s (native, 4 workers), 0 infra errors. 3 repeats: 0 flips.
Task 01 race test: 60 runs, 0 flips.

Caveat: the naive graders are deliberately minimal (6 of 10 have a single test), so 29 of 30 is
an upper bound on what a hurried author would miss, not an estimate of it.

## Three patterns (details in analysis/findings.md)
1. **State over time is invisible to one-shot examples.** Retry races, lost in-memory state,
   double reversals and expired holds all pass single-request tests.
2. **Numeric bugs live on measure-zero inputs.** Half-up vs banker's rounding, float drift and
   off-by-one tier bounds need *searched* tie and boundary inputs with an exact-arithmetic oracle.
3. **Counts and totals hide identity bugs.** Reconciliation that reuses a ledger entry, or keys
   not scoped per merchant, produce plausible totals with the wrong pairing.

Two grader-side lessons came from running valid code through every grader version: one hardened
grader silently dropped a regression test, and two produced false fails on valid code (a timeout
and a Windows file lock). Both were caught and logged.

## Limitations
- One author wrote every task, solution and grader; the wrong variants are predicted bugs, not
  observed model failures. Blind reviews were self-reviews; independent review is still owed.
- Verified natively on Windows with Python 3.14 and PostgreSQL 16.13. The Docker path was
  written but not run, so the "< 5 min in Docker" criterion is unmeasured.
- Harbor runtime conventions not in the public docs are labeled assumptions.

## Mapping to Datacurve
- **Task QA:** the naive → final matrix is a reusable QA procedure for any coding task: run
  starter, reference, a valid alternative and seeded wrong solutions against each grader version.
- **Verifier robustness:** the patterns above are checklists for reviewing verifiers at scale.
- **Format compatibility:** tasks export to Harbor, the format of Datacurve's public DeepSWE benchmark.
