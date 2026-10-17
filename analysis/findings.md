# Private draft — verifier hardening audit

Only measured outcomes belong here. Naive graders are committed before final graders.
All candidate data, accounts, merchants, and formats are synthetic.


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
- **Naive grader commit:** a418189 · **Hardened commit:** PENDING-04_ledger_reconciliation
- **What slipped through:** The unmodified starter satisfies ordinary examples but omits required behavior.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="04_ledger_reconciliation-wrong_no_consumption"></a>
### 04_ledger_reconciliation · wrong_no_consumption · false_pass under naive
- **Naive grader commit:** a418189 · **Hardened commit:** PENDING-04_ledger_reconciliation
- **What slipped through:** Allows one ledger payment to match multiple statement lines.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_duplicate_statement_line_left_unmatched` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="04_ledger_reconciliation-wrong_split_ignored"></a>
### 04_ledger_reconciliation · wrong_split_ignored · false_pass under naive
- **Naive grader commit:** a418189 · **Hardened commit:** PENDING-04_ledger_reconciliation
- **What slipped through:** Omits aggregate split matches.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_split_all_lines` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

<a id="04_ledger_reconciliation-wrong_refund_abs"></a>
### 04_ledger_reconciliation · wrong_refund_abs · false_pass under naive
- **Naive grader commit:** a418189 · **Hardened commit:** PENDING-04_ledger_reconciliation
- **What slipped through:** Treats negative statement amounts as payments of the absolute amount.
- **Why missed:** the ordinary example fixtures do not exercise this distinct state or boundary.
- **Hardening:** add observable tests `test_refund_kind_and_original_reference` plus the task invariants.
- **Lesson:** passing examples do not establish behavior across lifecycle, identity and numeric boundaries.

#### 04_ledger_reconciliation — measured naive summary (run a418189)
```text
runs=6 final_ok=0/0 naive_false_pass=4 infra_errors=0 flips=0 wall_s=2.153
```
