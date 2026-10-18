# Private draft — verifier hardening audit

Only measured outcomes belong here. Naive graders are committed before final graders.
All candidate data, accounts, merchants, and formats are synthetic.

### 10_batch_parser · starter · false_pass under final (2c3adf5)
- **What slipped through:** the unmodified starter ignored a nonzero declared-count mismatch.
- **Why missed:** final tests added mutation and atomicity cases but omitted the existing naive
  count regression. The full matrix exposed 9/9 starter tests passing.
- **Hardening:** retain the starter and add test_count_mismatch using the public parser.
- **Lesson:** hardening must preserve regression coverage from earlier grader versions.

### 08_refund_limits · reference · false_fail under final (fb4e73e)
- **Observed:** property assertions passed, but TemporaryDirectory cleanup raised WinError32 on
  an SQLite connection cycle awaiting garbage collection. No public API requires a close method.
- **Correction:** collect unreachable connection cycles before deleting the grader-owned fixture.
  Candidate code and all 200 generated refund sequences are unchanged. File deletion is fixture
  housekeeping, not observable refund behavior. The valid alternative already closes explicitly.
- **Lesson:** native resource cleanup must not accidentally become part of a financial contract.


<a id="01_idempotent_payments-wrong_retry_race"></a>
### 01_idempotent_payments · wrong_retry_race · false_pass under naive
- **Naive grader commit:** 9e13be2 · **Hardened commit:** cbad8db
- **What slipped through:** Checks before charging; concurrent requests each charge before insertion.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_concurrent_duplicates_charge_once` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="01_idempotent_payments-wrong_key_scope"></a>
### 01_idempotent_payments · wrong_key_scope · false_pass under naive
- **Naive grader commit:** 9e13be2 · **Hardened commit:** cbad8db
- **What slipped through:** Shares a key across merchants.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_same_key_different_merchants_independent` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="01_idempotent_payments-wrong_inmemory_cache"></a>
### 01_idempotent_payments · wrong_inmemory_cache · false_pass under naive
- **Naive grader commit:** 9e13be2 · **Hardened commit:** cbad8db
- **What slipped through:** App-local cache disappears at restart.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_replay_survives_app_restart` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 01_idempotent_payments — measured naive summary (run 9e13be2)
```text
runs=6 final_ok=0/0 naive_false_pass=3 infra_errors=0 flips=0 wall_s=8.638
```

#### 01_idempotent_payments — measured final summary (run cbad8db)
```text
runs=12 final_ok=6/6 naive_false_pass=3 infra_errors=0 flips=0 wall_s=22.766
```

<a id="02_interest_accrual-starter"></a>
### 02_interest_accrual · starter · false_pass under naive
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** The unmodified starter satisfies ordinary examples but omits required behavior.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="02_interest_accrual-wrong_float"></a>
### 02_interest_accrual · wrong_float · false_pass under naive
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** Binary floating point loses precision on ties and large principals.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_large_principal_exact, test_half_cent_ties_bankers` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="02_interest_accrual-wrong_half_up"></a>
### 02_interest_accrual · wrong_half_up · false_pass under naive
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** Rounds ties away from zero instead of to even.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_half_cent_ties_bankers` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="02_interest_accrual-wrong_round_daily"></a>
### 02_interest_accrual · wrong_round_daily · false_pass under naive
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** Rounds daily accrual before the posting boundary.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_small_balance_daily_accrues` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 02_interest_accrual — measured naive summary (run 6ab4600)
```text
runs=6 final_ok=0/0 naive_false_pass=4 infra_errors=0 flips=0 wall_s=2.410
```

#### 02_interest_accrual — measured final summary (run d86532e)
```text
runs=24 final_ok=12/12 naive_false_pass=7 infra_errors=0 flips=0 wall_s=24.668
```

<a id="04_ledger_reconciliation-starter"></a>
### 04_ledger_reconciliation · starter · false_pass under naive
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** The unmodified starter satisfies ordinary examples but omits required behavior.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="04_ledger_reconciliation-wrong_no_consumption"></a>
### 04_ledger_reconciliation · wrong_no_consumption · false_pass under naive
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** Allows one ledger payment to match multiple statement lines.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_duplicate_statement_line_left_unmatched` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="04_ledger_reconciliation-wrong_split_ignored"></a>
### 04_ledger_reconciliation · wrong_split_ignored · false_pass under naive
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** Omits aggregate split matches.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_split_all_lines` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="04_ledger_reconciliation-wrong_refund_abs"></a>
### 04_ledger_reconciliation · wrong_refund_abs · false_pass under naive
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** Treats negative statement amounts as payments of the absolute amount.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_refund_kind_and_original_reference` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 04_ledger_reconciliation — measured naive summary (run a418189)
```text
runs=6 final_ok=0/0 naive_false_pass=4 infra_errors=0 flips=0 wall_s=2.153
```

#### 04_ledger_reconciliation — measured final summary (run a432c4c)
```text
runs=36 final_ok=18/18 naive_false_pass=11 infra_errors=0 flips=0 wall_s=25.414
```

<a id="05_double_entry-wrong_cross_currency_sum"></a>
### 05_double_entry · wrong_cross_currency_sum · false_pass under naive
- **Naive grader commit:** 63820c1 · **Hardened commit:** 13285fe
- **What slipped through:** Balances the total across currencies instead of each currency.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_cross_currency_cannot_net` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="05_double_entry-wrong_non_atomic"></a>
### 05_double_entry · wrong_non_atomic · false_pass under naive
- **Naive grader commit:** 63820c1 · **Hardened commit:** 13285fe
- **What slipped through:** Commits individual lines before all account validation completes.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_unknown_account_is_atomic` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="05_double_entry-wrong_double_reverse"></a>
### 05_double_entry · wrong_double_reverse · false_pass under naive
- **Naive grader commit:** 63820c1 · **Hardened commit:** 13285fe
- **What slipped through:** Allows the same original transaction to be reversed twice.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_reverse_once` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 05_double_entry — measured naive summary (run 63820c1)
```text
runs=6 final_ok=0/0 naive_false_pass=3 infra_errors=0 flips=0 wall_s=4.274
```

### 05_double_entry ? valid candidates ? false_fail risk from verifier timeout
- **Observed at:** 9e15283; reference, alt_valid and wrong_double_reverse timed out at 90 s (infra_error, not a semantic FAIL).
- **Cause:** the state-machine invariant opened eight fresh connections after every generated operation, then re-checked the same unchanged accounts.
- **Correction:** preserve 20 examples ? 12 steps, all generated rules and the per-currency trial-balance invariant. Check both affected accounts on every successful post/reversal and verify the entire account model at teardown. This removes repeated I/O without removing operations or assertions on final state.
- **Scope:** do not interpret these timeout runs as candidate failures. A new complete matrix is required.

- **Follow-up:** disable shrinking for this database state machine. An already-failing candidate need not replay hundreds of smaller histories. All 20 generated examples, 12 steps and assertions remain; deterministic targeted tests still identify each intended defect.

#### 05_double_entry — measured final summary (run 13285fe)
```text
runs=48 final_ok=24/24 naive_false_pass=14 infra_errors=0 flips=0 wall_s=95.223
```

<a id="09_tiered_fees-starter"></a>
### 09_tiered_fees · starter · false_pass under naive
- **Naive grader commit:** f047a0b · **Hardened commit:** cfd4d2e
- **What slipped through:** The unmodified starter satisfies ordinary examples but omits required behavior.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="09_tiered_fees-wrong_exclusive_boundary"></a>
### 09_tiered_fees · wrong_exclusive_boundary · false_pass under naive
- **Naive grader commit:** f047a0b · **Hardened commit:** cfd4d2e
- **What slipped through:** Uses an exclusive upper tier boundary.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_inclusive_boundaries` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="09_tiered_fees-wrong_float_bps"></a>
### 09_tiered_fees · wrong_float_bps · false_pass under naive
- **Naive grader commit:** f047a0b · **Hardened commit:** cfd4d2e
- **What slipped through:** Binary percentage multiplication mis-rounds exact half-unit ties.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_discovered_float_ties` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 09_tiered_fees — measured naive summary (run f047a0b)
```text
runs=6 final_ok=0/0 naive_false_pass=3 infra_errors=0 flips=0 wall_s=2.074
```

#### 09_tiered_fees — measured final summary (run cfd4d2e)
```text
runs=60 final_ok=30/30 naive_false_pass=17 infra_errors=0 flips=0 wall_s=95.551
```

<a id="08_refund_limits-starter"></a>
### 08_refund_limits · starter · false_pass under naive
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** The unmodified starter satisfies ordinary examples but omits required behavior.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="08_refund_limits-wrong_checks_single_refund"></a>
### 08_refund_limits · wrong_checks_single_refund · false_pass under naive
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** Checks each refund against capture, ignoring earlier refunds.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_cumulative_partials` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="08_refund_limits-wrong_uses_authorized"></a>
### 08_refund_limits · wrong_uses_authorized · false_pass under naive
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** Uses the authorized amount as the refund ceiling.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_capture_less_than_authorization` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="08_refund_limits-wrong_counts_rejected"></a>
### 08_refund_limits · wrong_counts_rejected · false_pass under naive
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** Includes rejected attempts in the remaining refund budget.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_valid_after_rejection` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 08_refund_limits — measured naive summary (run a4adcfb)
```text
runs=6 final_ok=0/0 naive_false_pass=4 infra_errors=0 flips=0 wall_s=2.344
```

#### 08_refund_limits — measured final summary (run 28e2a21)
```text
runs=72 final_ok=36/36 naive_false_pass=21 infra_errors=0 flips=0 wall_s=71.630
```

<a id="07_statement_periods-starter"></a>
### 07_statement_periods · starter · false_pass under naive
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** The unmodified starter satisfies ordinary examples but omits required behavior.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="07_statement_periods-wrong_utc_month"></a>
### 07_statement_periods · wrong_utc_month · false_pass under naive
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** Uses UTC calendar months for every account.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_local_midnight_boundaries` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="07_statement_periods-wrong_inclusive_2359"></a>
### 07_statement_periods · wrong_inclusive_2359 · false_pass under naive
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** Ends at 23:59:59, excluding fractional seconds before midnight.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_microsecond_boundary` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="07_statement_periods-wrong_fixed_offset"></a>
### 07_statement_periods · wrong_fixed_offset · false_pass under naive
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** Keeps a standard-time offset throughout the year.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_dst_months` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 07_statement_periods — measured naive summary (run f5c24ac)
```text
runs=6 final_ok=0/0 naive_false_pass=4 infra_errors=0 flips=0 wall_s=1.441
```

#### 07_statement_periods — measured final summary (run 25de722)
```text
runs=84 final_ok=42/42 naive_false_pass=25 infra_errors=0 flips=0 wall_s=80.932
```

<a id="10_batch_parser-wrong_partial_accept"></a>
### 10_batch_parser · wrong_partial_accept · false_pass under naive
- **Naive grader commit:** 4b90fce · **Hardened commit:** 94c0302
- **What slipped through:** Accepts valid details from a batch containing invalid detail records.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_atomic_batch_rejection` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="10_batch_parser-wrong_ignores_hash_total"></a>
### 10_batch_parser · wrong_ignores_hash_total · false_pass under naive
- **Naive grader commit:** 4b90fce · **Hardened commit:** 94c0302
- **What slipped through:** Does not check the trailer account hash total.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_hash_total` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="10_batch_parser-wrong_crlf_slicing"></a>
### 10_batch_parser · wrong_crlf_slicing · false_pass under naive
- **Naive grader commit:** 4b90fce · **Hardened commit:** 94c0302
- **What slipped through:** Validates physical line width before normalizing CRLF.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_crlf` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 10_batch_parser — measured naive summary (run 4b90fce)
```text
runs=6 final_ok=0/0 naive_false_pass=3 infra_errors=0 flips=0 wall_s=1.560
```

<a id="03_fx_quotes-wrong_two_decimals"></a>
### 03_fx_quotes · wrong_two_decimals · false_pass under naive
- **Naive grader commit:** 295b342 · **Hardened commit:** 94c0302
- **What slipped through:** Assumes every currency has two decimal places.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_jpy_and_kwd_units` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="03_fx_quotes-wrong_round_cross_leg"></a>
### 03_fx_quotes · wrong_round_cross_leg · false_pass under naive
- **Naive grader commit:** 295b342 · **Hardened commit:** 94c0302
- **What slipped through:** Rounds the intermediate USD amount in a cross quote.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_cross_has_no_intermediate_rounding` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="03_fx_quotes-wrong_fee_after_conversion"></a>
### 03_fx_quotes · wrong_fee_after_conversion · false_pass under naive
- **Naive grader commit:** 295b342 · **Hardened commit:** 94c0302
- **What slipped through:** Rounds destination fees after conversion instead of source fees before it.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_source_fee_before_conversion` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 03_fx_quotes — measured naive summary (run 295b342)
```text
runs=6 final_ok=0/0 naive_false_pass=3 infra_errors=0 flips=0 wall_s=1.901
```

<a id="06_available_balance-wrong_available_ignores_holds"></a>
### 06_available_balance · wrong_available_ignores_holds · false_pass under naive
- **Naive grader commit:** 6cf4a11 · **Hardened commit:** PENDING-06_available_balance
- **What slipped through:** Authorizes against posted funds, ignoring existing holds.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_existing_holds_reduce_available` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="06_available_balance-wrong_partial_capture_keeps_remainder"></a>
### 06_available_balance · wrong_partial_capture_keeps_remainder · false_pass under naive
- **Naive grader commit:** 6cf4a11 · **Hardened commit:** PENDING-06_available_balance
- **What slipped through:** Leaves the remainder held after a partial capture.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_partial_capture_releases_remainder` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="06_available_balance-wrong_expired_holds_count"></a>
### 06_available_balance · wrong_expired_holds_count · false_pass under naive
- **Naive grader commit:** 6cf4a11 · **Hardened commit:** PENDING-06_available_balance
- **What slipped through:** Counts expired active records against availability.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_expiry_exactly_seven_days` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 06_available_balance — measured naive summary (run 6cf4a11)
```text
runs=6 final_ok=0/0 naive_false_pass=3 infra_errors=0 flips=0 wall_s=3.535
```

#### 10_batch_parser — measured final summary (run 94c0302)
```text
runs=108 final_ok=54/54 naive_false_pass=31 infra_errors=0 flips=0 wall_s=116.892
```

#### 03_fx_quotes — measured final summary (run 94c0302)
```text
runs=108 final_ok=54/54 naive_false_pass=31 infra_errors=0 flips=0 wall_s=116.892
```

#### 06_available_balance — measured final summary (run 3645a05, re-measured at 451d92e)
```text
runs=12 final_ok=6/6 naive_false_pass=3 infra_errors=0 flips=0 wall_s=50.634
```

#### Full matrix — committed snapshot (results/final/matrix.json)
```text
runs=120 final_ok=60/60 naive_false_pass=34 infra_errors=0 flips=0 wall_s=173.865
```
Naive graders let through 29 of 30 wrong variants and 5 of 10 unmodified starters. The one
wrong variant the naive grader caught was 09 `wrong_marginal` (its mid-tier examples already
disagree with marginal pricing), and even that was flagged `ok_wrong_reason`.

## v2 redesign entries (review R1, docs/REVIEW-2026-10-17.md)

IDs F-0xx are the v1 audit; F-1xx are the v2 task redesigns. A v2 redesign replaces the starter,
the wrong variants and the naive grader of a task; the v1 entries for that task are kept above
and marked superseded. Naive runs are `run_all --tasks NN --grader all` on a clean tree.

<a id="04_ledger_reconciliation-v2"></a>
### F-101 · 04_ledger_reconciliation · v2 redesign
- **Why v1 was redesigned:** review R1. The v1 starter differed from the reference by 4 changed
  lines (`== 0` became `<= 3`, twice), so the ticket was "find the one-line bug" and the wrong
  variants described bugs in code the starter already got right. By the new `regressive_wrong`
  metric, 2 of the 3 v1 wrongs (`wrong_no_consumption`, `wrong_refund_abs`) broke `must_fail`
  tests that the v1 starter passed. v1 entries for this task are **superseded by v2**.
- **v2 starter:** exact same-day R1 matching only, no ledger consumption, every unmatched line
  reported as `no_match`; plus CSV/report/preview support code (209 non-test lines). Window,
  consumption, R2 split, R3 refund and R4 duplicate classification are the ticket.
  `ref_diff_lines` 4 -> 64 (floor 40).
- **v2 wrong variants (completions of the new starter):** `wrong_no_consumption` (adds window, R2,
  R3, R4; keeps the starter's non-consuming candidate lookup), `wrong_split_ignored` (everything
  except R2), `wrong_refund_abs` (absolute amounts in the exact rule). None is regressive.
- **Naive grader (commit e1b318e):** 3 tests, count-based: `test_clean_one_to_one`,
  `test_ticket_worked_example` (`len(matches) == 2`, nothing unmatched), `test_unrelated_line_is_unmatched`.
  Observed: `wrong_no_consumption` false_pass, `wrong_refund_abs` false_pass, `wrong_split_ignored`
  **caught** (`ok_wrong_reason`: the worked example contains a split, so the naive grader failed
  it via `test_ticket_worked_example`, not via the declared `test_split_all_lines`). Unmodified
  starter fails the worked example (correctly). Predictions matched all three.
- **Hardened commit:** e1b318e. The v1 final grader (6 tests incl. the ground-truth hypothesis
  property) needed no change: all variants `ok` under final, starter fails 5 of 6 final tests.
```text
runs=12 final_ok=6/6 naive_false_pass=2 infra_errors=0 flips=0 wall_s=4.555
```

<a id="05_double_entry-v2"></a>
### F-102 · 05_double_entry · v2 redesign
- **Why v1 was redesigned:** review R1. The v1 starter differed from the reference by 2 changed
  lines (the per-currency balance check), so "enforce the invariant" was a one-line bug hunt and
  `wrong_non_atomic` / `wrong_double_reverse` described features the starter already had. v1
  entries for this task are **superseded by v2**.
- **v2 starter:** autocommit connection; lines are inserted one by one with no balance
  validation, no transaction wrapper and no reversal (`reverse` and the reversal columns do not
  exist); plus formatting and CSV import support code (211 non-test lines). `ref_diff_lines` 2 -> 52 (floor 40).
- **v2 wrong variants:** `wrong_cross_currency_sum` (validates one grand total),
  `wrong_non_atomic` (adds validation and reversal but keeps the starter's autocommit connection and
  validates while inserting), `wrong_double_reverse` (reversal without the once-only check). None is regressive.
- **Naive grader (commit 72eacbc):** 3 tests: `test_balanced_post`, `test_unbalanced_rejected`
  (single-currency, asserts only `pytest.raises`), `test_ticket_example_post_then_reverse`
  (balances only). All three wrongs are **false_pass**, as predicted: every naive fixture is
  single-currency (so grand-total balancing is indistinguishable), no fixture reverses twice, and
  no fixture references an unknown account or inspects state after a rejection. The unmodified
  starter fails two naive tests (`test_unbalanced_rejected`, `test_ticket_example_post_then_reverse`).
- **Hardened commit:** 72eacbc. The v1 final grader (10 tests incl. the stateful machine) needed
  no change. Side observation: `wrong_non_atomic` also fails `test_cross_currency_cannot_net`
  because its rejected cross-currency post leaves lines behind, which the test's trial-balance
  comparison sees; the declared `test_unknown_account_is_atomic` also fails.
```text
runs=12 final_ok=6/6 naive_false_pass=3 infra_errors=0 flips=0 wall_s=71.753
```

<a id="06_available_balance-v2"></a>
### F-103 · 06_available_balance · v2 redesign
- **Why v1 was redesigned:** review R1. The v1 starter differed from the reference by 2 lines (one
  `UPDATE accounts SET posted=posted-?`), and 2 of the 3 v1 wrongs described holds behaviour the v1
  starter already implemented (it already counted active holds, expired them and closed them on
  capture). v1 entries for this task are **superseded by v2**. Also the v1 starter (191 lines, tests
  included) failed S1.
- **v2 starter:** authorizations are recorded and approved against `posted + overdraft`, but
  `available_minor == posted_minor`; there is no holds model, no capture or void route and no
  expiry; plus CLI, CSV export, seed and manual-clock support code (about 215 non-test lines).
  `ref_diff_lines` 2 -> 40 (floor 25).
- **v2 wrong variants:** `wrong_available_ignores_holds` (capture/void/expiry added, starter
  availability kept), `wrong_partial_capture_keeps_remainder` (leaves the unused part held),
  `wrong_expired_holds_count` (holds counted without the expiry cut-off). None is regressive.
- **Naive grader (commit 4c7bb1c):** 3 tests: `test_full_capture`, `test_ticket_worked_example`
  (authorize 3000, available 7000; capture 1200, posted/available 8800), `test_invalid_amount_rejected`.
  Because the ticket's own example now shows the hold reducing `available` and the remainder being
  released, the naive grader **caught** `wrong_available_ignores_holds` and
  `wrong_partial_capture_keeps_remainder` (both `ok_wrong_reason`: they fail
  `test_ticket_worked_example`, not the declared must_fail tests). `wrong_expired_holds_count` is a
  **false_pass**: the naive clock never moves, so no fixture can distinguish an expired hold from an
  active one. The unmodified starter fails `test_full_capture` and `test_ticket_worked_example`.
  All predictions matched.
- **Hardened commit:** 4c7bb1c. The v1 final grader (6 tests incl. the random operation model) needed no change.
```text
runs=12 final_ok=6/6 naive_false_pass=1 infra_errors=0 flips=0 wall_s=48.248
```

<a id="09_tiered_fees-v2"></a>
### F-104 · 09_tiered_fees · v2 redesign
- **Why v1 was redesigned:** review R1. The v1 starter differed from the reference by 2 changed
  lines (the clamp). It already selected tiers, rounded half up in integer arithmetic and validated
  everything, so all three v1 wrongs (`wrong_exclusive_boundary`, `wrong_float_bps`, `wrong_marginal`)
  were regressions of code the starter got right. v1 entries for this task are **superseded by v2**.
  The v1 starter (198 lines including tests) also failed S1.
- **v2 starter:** prices every amount with the first tier's rate using truncating integer division;
  no tier selection, half-up rounding, clamp, amount validation or schedule validation (the latter
  moved from the `Schedule` constructor into `compute_fee`, and PROBLEM.md now says so); plus
  loader, catalog and report support code (216 non-test lines). `ref_diff_lines` 2 -> 35 (floor 25).
- **v2 wrong variants:** `wrong_exclusive_boundary` (`<` in tier selection), `wrong_float_bps`
  (half-up via a float percentage), `wrong_marginal` (bands priced separately). None is regressive.
- **Naive grader (commit e0e65b9):** 3 tests: `test_tier_midpoints` (5000/15000/30000, no clamp),
  `test_ticket_worked_example_with_clamps` (adds amounts 100 and 30000 against a 25/100 clamp, away
  from every tier boundary), `test_negative_amount_rejected`. `wrong_exclusive_boundary` and
  `wrong_float_bps` are **false_pass**: no naive amount sits on a boundary or on a half-unit
  tie. `wrong_marginal` is **caught** (`ok_wrong_reason`: `test_tier_midpoints` and
  `test_ticket_worked_example_with_clamps` fail because 15000 prices to 145, not 95). All predictions
  matched; the unmodified starter fails all three naive tests.
- **Hardened commit:** 68ae615. One final-grader addition:
  `test_invalid_schedule_raises_for_any_amount` (six invalid schedules x three amounts), because
  schedule validation is now a compute_fee obligation. Every variant stayed `ok` under final.
```text
runs=12 final_ok=6/6 naive_false_pass=2 infra_errors=0 flips=0 wall_s=5.838
```

<!-- v2-entries-end -->

## Patterns

1. **State over time is invisible to one-shot examples.** 01 `wrong_retry_race`,
   01 `wrong_inmemory_cache`, 05 `wrong_double_reverse`, 06 `wrong_expired_holds_count` and
   08 `wrong_checks_single_refund` each behave correctly for any single request. The bug appears
   only across a second request, a restart, a clock advance or a concurrent caller. Hardened
   graders needed sequences, restarts, fake clocks and a barrier-synchronized race.
2. **Numeric bugs live on measure-zero inputs.** 02 `wrong_half_up`, 02 `wrong_float`,
   03 `wrong_round_cross_leg`, 09 `wrong_float_bps`, 09 `wrong_exclusive_boundary` and
   07 `wrong_inclusive_2359` agree with the reference on almost every input. A tolerance check
   (`abs(diff) <= 0.01`) or "one mid-tier value" passes all of them. The fix is searched tie and
   boundary inputs (`tools/find_ties.py`), cross-checked by exact Fraction arithmetic
   (`tools/verify_cases.py`), and exact type and exponent assertions.
3. **Counts and totals hide identity and scope bugs.** 04 `wrong_no_consumption`,
   04 `wrong_refund_abs`, 01 `wrong_key_scope`, 05 `wrong_cross_currency_sum` and
   08 `wrong_uses_authorized` produce plausible totals or match counts with the wrong pairing,
   namespace or base. Asserting on sets of id pairs, per-scope results and per-currency
   invariants catches them.
4. **Rejection paths need state assertions, not just error assertions.** 05 `wrong_non_atomic`,
   10 `wrong_partial_accept` and 08 `wrong_counts_rejected` raise or report the right error, but
   leave the system in the wrong state. Every hardened grader now checks observable state
   (trial balance, payments list, the next valid refund) after each rejected operation.
5. **Hardening itself regresses.** The first hardened grader for task 10 dropped the naive
   count-mismatch test, so the unmodified starter passed 9/9 final tests. Graders for 05 and 08
   first produced false fails on valid code (a timeout from redundant database I/O, and a Windows
   file-lock in fixture cleanup). Running the starter and alt_valid through every grader version
   is what exposed these.

## Limitations

- Every task, solution and grader was written by one author. The wrong variants are the bugs that author predicted. Real model failures may
  cluster differently (see the M5 stretch goal, not run).
- The blind reviews (S5) are disciplined self-reviews, not independent reviews. GATES.md tracks
  the independent review that is still owed.
- Verified natively on Windows 11 with Python 3.14 and PostgreSQL 16.13. The Docker path
  (Python 3.12 image) was written but not executed, so S4 is unmeasured.
- The Harbor export follows only documented task.toml keys. Mount paths and compose conventions
  are labeled assumptions, validated by a local simulation rather than the Harbor runtime.
- Isolation is for reproducibility, not for hostile code. Candidate code runs as the same user.

## Implications for task authoring at scale

- Run the unmodified starter and a structurally different valid solution through every grader
  version. Both caught grader defects here (a dropped regression, an overfitted fixture) that
  reference-only checks would have missed.
- For numeric tasks, require searched tie and boundary inputs with an exact-arithmetic oracle.
  Hand-picked examples nearly never land on the inputs that separate correct from plausible code.
- Require at least one stateful test (sequence, restart, clock or concurrency) for any task
  whose ticket mentions persistence, retries, limits or lifecycle.
- Treat "fails for the declared reason" (`must_fail`) as part of grader QA. A wrong solution that
  fails for an incidental reason is a latent false pass for the next variant.
