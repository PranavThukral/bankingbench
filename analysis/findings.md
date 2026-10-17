# Private draft — verifier hardening audit

Only measured outcomes belong here. Naive graders are committed before final graders.
All candidate data, accounts, merchants, and formats are synthetic.

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
- **Naive grader commit:** f5c24ac · **Hardened commit:** PENDING-07_statement_periods
- **What slipped through:** The unmodified starter satisfies ordinary examples but omits required behavior.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="07_statement_periods-wrong_utc_month"></a>
### 07_statement_periods · wrong_utc_month · false_pass under naive
- **Naive grader commit:** f5c24ac · **Hardened commit:** PENDING-07_statement_periods
- **What slipped through:** Uses UTC calendar months for every account.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_local_midnight_boundaries` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="07_statement_periods-wrong_inclusive_2359"></a>
### 07_statement_periods · wrong_inclusive_2359 · false_pass under naive
- **Naive grader commit:** f5c24ac · **Hardened commit:** PENDING-07_statement_periods
- **What slipped through:** Ends at 23:59:59, excluding fractional seconds before midnight.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_microsecond_boundary` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="07_statement_periods-wrong_fixed_offset"></a>
### 07_statement_periods · wrong_fixed_offset · false_pass under naive
- **Naive grader commit:** f5c24ac · **Hardened commit:** PENDING-07_statement_periods
- **What slipped through:** Keeps a standard-time offset throughout the year.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_dst_months` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 07_statement_periods — measured naive summary (run f5c24ac)
```text
runs=6 final_ok=0/0 naive_false_pass=4 infra_errors=0 flips=0 wall_s=1.441
```
