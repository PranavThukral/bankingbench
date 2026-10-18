# Private draft — verifier hardening audit

Only measured outcomes belong here. Naive graders are committed before final graders.
All candidate data, accounts, merchants, and formats are synthetic.

**Numbering.** `F-0xx` entries are the v1 audit (the original build). `F-1xx` entries are the v2 task
redesigns required by review R1 (`docs/REVIEW-2026-10-17.md`), each with its own
`run_all --tasks NN --grader all` block. `F-2xx` entries are the per-variant findings of the v2
variants. Anchors: `#<task>-<variant>` is the current (v2) entry that the report links to; the v1
entry of a redesigned variant has the suffix `-v1`. A v1 entry says which F-1xx entry supersedes it.

## v1 audit

Sections below are the v1 record. Entries marked *superseded* describe a starter, variant or naive grader
that was replaced in v2; they are kept unchanged in substance. The cumulative v1 summary blocks
(which mixed several tasks, and shared one block between tasks 03 and 10) were removed: each task now has
its own measured block in its F-1xx entry.

<a id="10_batch_parser-starter-v1"></a>
### F-001 · 10_batch_parser · starter · false_pass under final (hardening regression, v1, superseded)
- **Hardened commit:** 2c3adf5 (the final grader as first written).
- **What slipped through:** the unmodified v1 starter ignored a nonzero declared-count mismatch yet passed all 9 final tests.
- **Why the final grader missed it:** the hardened tests added mutation and atomicity cases but dropped the naive grader's
  `test_count_mismatch` (a trailer count of 2 over one detail line, asserting `count_mismatch`). The full-matrix run exposed 9/9 starter tests passing.
- **Hardening:** restored `test_count_mismatch` in the final grader, using the public parser.
- **Lesson:** hardening must preserve regression coverage from earlier grader versions; running the unmodified starter through every grader version finds a dropped test.
- **Superseded by v2:** F-105 (the v1 starter is replaced; the lesson stands).

<a id="08_refund_limits-reference-v1"></a>
### F-002 · 08_refund_limits · reference · false_fail under final (fixture cleanup, v1)
- **Hardened commit:** fb4e73e.
- **Observed:** the property test `test_refund_sequence_matches_greedy_oracle` passed, but `TemporaryDirectory` cleanup raised `WinError 32` on an SQLite connection cycle awaiting garbage collection. No public API requires a close method.
- **Correction:** collect unreachable connection cycles before deleting the grader-owned fixture. Candidate code and all 200 generated refund sequences are unchanged. File deletion is fixture housekeeping, not observable refund behavior. The valid alternative already closes explicitly.
- **Lesson:** native resource cleanup must not accidentally become part of a financial contract. (Still in force: the v2 final grader keeps the `gc.collect()` in its `workspace()` fixture.)

<a id="05_double_entry-timeout-v1"></a>
### F-003 · 05_double_entry · valid candidates · false_fail risk from verifier timeout (v1)
- **Observed at:** 9e15283; reference, alt_valid and wrong_double_reverse timed out at 90 s (`infra_error`, not a semantic FAIL).
- **Cause:** the state-machine invariant opened eight fresh connections after every generated operation, then re-checked the same unchanged accounts.
- **Correction:** keep 20 examples x 12 steps, all generated rules and the per-currency trial-balance invariant; check both affected accounts on every successful post or reversal and verify the whole account model at teardown. This removes repeated I/O without removing operations or assertions on final state.
- **Follow-up:** disable shrinking for this database state machine, so an already-failing candidate does not replay hundreds of smaller histories. All 20 generated examples, 12 steps and assertions remain; deterministic targeted tests still identify each intended defect.
- **Scope:** do not read the timeout runs as candidate failures. A new complete matrix was required and taken (hardened commit 13285fe).
- **Lesson:** a state-machine test whose cost grows with history length needs a budget, or a slow valid solution becomes a false fail.

<a id="01_idempotent_payments-wrong_retry_race"></a>
### F-004 · 01_idempotent_payments · wrong_retry_race · false_pass under naive
- **Naive grader commit:** 9e13be2 · **Hardened commit:** cbad8db
- **What slipped through:** Checks for the key, charges, then inserts; two simultaneous duplicates both reach the gateway.
- **Why the naive grader missed it:** `test_retry` sends the duplicate only after the first response has returned and asserts `len(gateway.calls) == 1`. Sequentially, the check-then-insert variant finds the committed key and makes one call as well. No naive test sends two requests at once, and the naive `FakeGateway` has no latency to widen the window.
- **Hardening:** final tests that fail this variant: `test_concurrent_duplicates_charge_once`, `test_body_mismatch_while_in_flight`.
- **Lesson:** A sequential retry cannot tell a check-then-insert from a reservation. The grader needs simultaneous duplicates behind a barrier and a gateway slow enough to widen the race window.

<a id="01_idempotent_payments-wrong_key_scope"></a>
### F-005 · 01_idempotent_payments · wrong_key_scope · false_pass under naive
- **Naive grader commit:** 9e13be2 · **Hardened commit:** cbad8db
- **What slipped through:** Shares one key namespace across merchants.
- **Why the naive grader missed it:** Every naive request uses a single merchant (`merchant_retry`, `merchant_visible`), and `test_retry` compares two responses for the same merchant, so a namespace shared across merchants behaves identically.
- **Hardening:** final tests that fail this variant: `test_same_key_different_merchants_independent`.
- **Lesson:** Scope bugs need two principals in one fixture.

<a id="01_idempotent_payments-wrong_inmemory_cache"></a>
### F-006 · 01_idempotent_payments · wrong_inmemory_cache · false_pass under naive
- **Naive grader commit:** 9e13be2 · **Hardened commit:** cbad8db
- **What slipped through:** Keeps replay state in a process-local dict, which disappears at restart.
- **Why the naive grader missed it:** `test_retry` builds one app and sends both requests through it, so an in-process cache still replays. No naive test constructs a second `create_app` on the same database.
- **Hardening:** final tests that fail this variant: `test_replay_survives_app_restart`.
- **Lesson:** A persistence requirement needs a restart (a second app instance on the same database) in the fixture.

<a id="02_interest_accrual-starter-v1"></a>
### F-007 · 02_interest_accrual · starter · false_pass under naive (v1, superseded)
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** The unmodified float starter passed the naive grader.
- **Why the naive grader missed it:** `test_examples` has three simple_monthly cases (1000, 2000 and 5000 CAD at 0.0365 for one 31-day month) and accepts any result within `abs(diff) <= 0.01`; float arithmetic is accurate to about 1e-12 there. The starter only fails on partial months, which `test_examples` never uses.
- **Hardening:** final tests that fail this starter: `test_half_cent_ties_bankers (3 cases)`, `test_large_principal_exact (both methods)`, `test_leap_and_partial`, `test_accrual_properties`.
- **Superseded by v2:** F-109 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="02_interest_accrual-wrong_float-v1"></a>
### F-008 · 02_interest_accrual · wrong_float · false_pass under naive (v1, superseded)
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** Uses binary floating point and `round(x, 2)`; wrong on large principals and on ties.
- **Why the naive grader missed it:** The `0.01` tolerance in `test_examples` absorbs any float error, and no naive principal exceeds 5000 or lands on a half-cent tie.
- **Hardening:** final tests that fail this variant: `test_half_cent_ties_bankers (3 cases)`.
- **Lesson:** A tolerance equal to the unit being tested makes the assertion unable to see rounding at all.
- **Superseded by v2:** F-109 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="02_interest_accrual-wrong_half_up-v1"></a>
### F-009 · 02_interest_accrual · wrong_half_up · false_pass under naive (v1, superseded)
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** Rounds exact ties away from zero instead of to even.
- **Why the naive grader missed it:** None of the three naive results is an exact half-cent tie (3.10, 6.20 and 15.50 are exact), so the rounding mode is never consulted, and the 0.01 tolerance would hide a one-cent difference anyway.
- **Hardening:** final tests that fail this variant: `test_half_cent_ties_bankers (3 cases)`.
- **Lesson:** Rounding-mode bugs only exist on constructed ties; they need searched inputs.
- **Superseded by v2:** F-109 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="02_interest_accrual-wrong_round_daily-v1"></a>
### F-010 · 02_interest_accrual · wrong_round_daily · false_pass under naive (v1, superseded)
- **Naive grader commit:** 6ab4600 · **Hardened commit:** d86532e
- **What slipped through:** Rounds each day's accrual to cents before the posting boundary.
- **Why the naive grader missed it:** Each daily accrual in `test_examples` (1000, 2000, 5000 x 0.0365 / 365) is exactly 0.10, 0.20 or 0.50, already whole cents, so rounding it daily changes nothing. No test uses a small balance.
- **Hardening:** final tests that fail this variant: `test_small_balance_daily_accrues`, `test_large_principal_exact (both methods)`.
- **Superseded by v2:** F-109 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="03_fx_quotes-wrong_two_decimals-v1"></a>
### F-011 · 03_fx_quotes · wrong_two_decimals · false_pass under naive (v1, superseded)
- **Naive grader commit:** 295b342 · **Hardened commit:** 94c0302
- **What slipped through:** Assumes two decimal places for every currency.
- **Why the naive grader missed it:** `test_direct_cad_usd` is a single CAD to USD quote; both currencies have two decimal places, so a universal scale of 2 gives the same answer.
- **Hardening:** final tests that fail this variant: `test_jpy_and_kwd_units`, `test_exact_scaling_and_monotonicity`.
- **Superseded by v2:** F-110 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="03_fx_quotes-wrong_round_cross_leg-v1"></a>
### F-012 · 03_fx_quotes · wrong_round_cross_leg · false_pass under naive (v1, superseded)
- **Naive grader commit:** 295b342 · **Hardened commit:** 94c0302
- **What slipped through:** Rounds the intermediate USD amount of a cross quote to cents.
- **Why the naive grader missed it:** The only naive quote is a direct pair, so no cross leg exists to round.
- **Hardening:** final tests that fail this variant: `test_cross_has_no_intermediate_rounding`.
- **Superseded by v2:** F-110 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="03_fx_quotes-wrong_fee_after_conversion-v1"></a>
### F-013 · 03_fx_quotes · wrong_fee_after_conversion · false_pass under naive (v1, superseded)
- **Naive grader commit:** 295b342 · **Hardened commit:** 94c0302
- **What slipped through:** Converts the gross amount and subtracts a destination-side fee instead of deducting a source fee first.
- **Why the naive grader missed it:** `test_direct_cad_usd` asserts `converted_minor == 7425` and `fee_minor == 100` for 10000 at 0.75 and 100 bps. 7500 - 75 and 0.75 x 9900 are both 7425 and no rounding occurs, so the two orders agree.
- **Hardening:** final tests that fail this variant: `test_source_fee_before_conversion`, `test_jpy_and_kwd_units`.
- **Lesson:** When arithmetic is linear and exact, order-of-operations bugs are invisible; the fixture needs a rounding step between the orders.
- **Superseded by v2:** F-110 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="04_ledger_reconciliation-starter-v1"></a>
### F-014 · 04_ledger_reconciliation · starter · false_pass under naive (v1, superseded)
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** The v1 starter (same-day window, otherwise the reference) passed the naive grader.
- **Why the naive grader missed it:** `test_clean_one_to_one` builds three same-day, one-to-one pairs and asserts `len(matches) == 3`. The v1 starter's only deviation was the date window, which same-day records never exercise.
- **Hardening:** final tests that fail this starter: `test_split_all_lines`, `test_tie_breaks_and_window`.
- **Superseded by v2:** F-101 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="04_ledger_reconciliation-wrong_no_consumption-v1"></a>
### F-015 · 04_ledger_reconciliation · wrong_no_consumption · false_pass under naive (v1, superseded)
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** Lets one ledger payment match several statement lines.
- **Why the naive grader missed it:** `test_clean_one_to_one` gives each statement line its own ledger entry and asserts only the count, so a variant that never marks entries used returns the same three matches.
- **Hardening:** final tests that fail this variant: `test_duplicate_statement_line_left_unmatched`, `test_ground_truth_transforms`.
- **Lesson:** Count assertions hide identity reuse; assert the set of id pairs.
- **Superseded by v2:** F-101 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="04_ledger_reconciliation-wrong_split_ignored-v1"></a>
### F-016 · 04_ledger_reconciliation · wrong_split_ignored · false_pass under naive (v1, superseded)
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** Implements exact matching only and omits aggregate split matches.
- **Why the naive grader missed it:** The naive fixture has no statement group that sums to a ledger amount; `len(matches) == 3` is satisfied by exact matches alone.
- **Hardening:** final tests that fail this variant: `test_split_all_lines`, `test_ground_truth_transforms`.
- **Superseded by v2:** F-101 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="04_ledger_reconciliation-wrong_refund_abs-v1"></a>
### F-017 · 04_ledger_reconciliation · wrong_refund_abs · false_pass under naive (v1, superseded)
- **Naive grader commit:** a418189 · **Hardened commit:** a432c4c
- **What slipped through:** Compares absolute amounts and so treats a negative statement line as a payment.
- **Why the naive grader missed it:** No naive statement amount is negative, so `abs()` is the identity.
- **Hardening:** final tests that fail this variant: `test_refund_kind_and_original_reference`.
- **Superseded by v2:** F-101 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="05_double_entry-wrong_cross_currency_sum-v1"></a>
### F-018 · 05_double_entry · wrong_cross_currency_sum · false_pass under naive (v1, superseded)
- **Naive grader commit:** 63820c1 · **Hardened commit:** 13285fe
- **What slipped through:** Balances one grand total across currencies instead of each currency.
- **Why the naive grader missed it:** `accounts()` in the naive grader creates both accounts in CAD, so the grand total and the per-currency total are the same number.
- **Hardening:** final tests that fail this variant: `test_cross_currency_cannot_net`, `TestJournal (stateful machine)`.
- **Lesson:** A fixture with a single currency cannot test a per-currency invariant.
- **Superseded by v2:** F-102 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="05_double_entry-wrong_non_atomic-v1"></a>
### F-019 · 05_double_entry · wrong_non_atomic · false_pass under naive (v1, superseded)
- **Naive grader commit:** 63820c1 · **Hardened commit:** 13285fe
- **What slipped through:** Writes lines one at a time, so a later failure leaves earlier lines behind.
- **Why the naive grader missed it:** `test_unbalanced_rejected` asserts only `pytest.raises(UnbalancedTransaction)` and never reads a balance or the trial balance afterwards; no naive post references an unknown account.
- **Hardening:** final tests that fail this variant: `test_unknown_account_is_atomic`, `test_rejections_leave_no_trace`, `test_cross_currency_cannot_net`.
- **Lesson:** An error assertion does not prove the rejection left no trace; read state after it.
- **Superseded by v2:** F-102 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="05_double_entry-wrong_double_reverse-v1"></a>
### F-020 · 05_double_entry · wrong_double_reverse · false_pass under naive (v1, superseded)
- **Naive grader commit:** 63820c1 · **Hardened commit:** 13285fe
- **What slipped through:** Omits the once-only check, so a transaction can be reversed twice.
- **Why the naive grader missed it:** Neither naive test (`test_balanced_post`, `test_unbalanced_rejected`) calls `reverse`.
- **Hardening:** final tests that fail this variant: `test_reverse_once`, `TestJournal (stateful machine)`.
- **Superseded by v2:** F-102 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="06_available_balance-wrong_available_ignores_holds-v1"></a>
### F-021 · 06_available_balance · wrong_available_ignores_holds · false_pass under naive (v1, superseded)
- **Naive grader commit:** 6cf4a11 · **Hardened commit:** 3645a05
- **What slipped through:** Authorizes against posted funds and reports available == posted, ignoring open holds.
- **Why the naive grader missed it:** `test_full_capture` authorizes once, captures the full amount and asserts `posted == available == 9000`; once the hold is captured and closed, availability is the same whether or not holds were counted. `test_initial_balance` has no hold.
- **Hardening:** final tests that fail this variant: `test_existing_holds_reduce_available`, `test_overdraft_boundary`, `test_random_operation_model`.
- **Superseded by v2:** F-103 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="06_available_balance-wrong_partial_capture_keeps_remainder-v1"></a>
### F-022 · 06_available_balance · wrong_partial_capture_keeps_remainder · false_pass under naive (v1, superseded)
- **Naive grader commit:** 6cf4a11 · **Hardened commit:** 3645a05
- **What slipped through:** Leaves the unused remainder of a partially captured hold active.
- **Why the naive grader missed it:** `test_full_capture` captures the full held amount (1000 of 1000), so there is no remainder to release.
- **Hardening:** final tests that fail this variant: `test_partial_capture_releases_remainder`, `test_random_operation_model`.
- **Superseded by v2:** F-103 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="06_available_balance-wrong_expired_holds_count-v1"></a>
### F-023 · 06_available_balance · wrong_expired_holds_count · false_pass under naive (v1, superseded)
- **Naive grader commit:** 6cf4a11 · **Hardened commit:** 3645a05
- **What slipped through:** Keeps counting expired holds against availability.
- **Why the naive grader missed it:** The naive `Clock` always returns 2026-01-01 and no test advances it, so no hold ever ages.
- **Hardening:** final tests that fail this variant: `test_expiry_exactly_seven_days`, `test_random_operation_model`.
- **Lesson:** Time-dependent rules need a fake clock the test can move.
- **Superseded by v2:** F-103 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="07_statement_periods-starter-v1"></a>
### F-024 · 07_statement_periods · starter · false_pass under naive (v1, superseded)
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** The v1 starter (UTC months) passed the naive grader.
- **Why the naive grader missed it:** `test_midmonth_utc` selects one mid-month transaction for `account_tz='UTC'`; for a UTC account the UTC month is the local month.
- **Hardening:** final tests that fail this starter: `test_local_midnight_boundaries (Toronto, Kolkata)`, `test_dst_months (3 zones)`, `test_naive_and_instant_order`.
- **Superseded by v2:** F-106 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="07_statement_periods-wrong_utc_month-v1"></a>
### F-025 · 07_statement_periods · wrong_utc_month · false_pass under naive (v1, superseded)
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** Uses UTC calendar months for every account.
- **Why the naive grader missed it:** Same single UTC fixture as above: `test_midmonth_utc` cannot distinguish UTC boundaries from account-local ones.
- **Hardening:** final tests that fail this variant: `test_local_midnight_boundaries (Toronto, Kolkata)`, `test_dst_months (3 zones)`.
- **Superseded by v2:** F-106 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="07_statement_periods-wrong_inclusive_2359-v1"></a>
### F-026 · 07_statement_periods · wrong_inclusive_2359 · false_pass under naive (v1, superseded)
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** Ends the period at 23:59:59, dropping the final fractional second.
- **Why the naive grader missed it:** `test_midmonth_utc` uses 2026-01-15 midnight, far from any boundary.
- **Hardening:** final tests that fail this variant: `test_microsecond_boundary`, `test_local_midnight_boundaries`, `test_thirteen_month_partition`.
- **Superseded by v2:** F-106 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="07_statement_periods-wrong_fixed_offset-v1"></a>
### F-027 · 07_statement_periods · wrong_fixed_offset · false_pass under naive (v1, superseded)
- **Naive grader commit:** f5c24ac · **Hardened commit:** 25de722
- **What slipped through:** Uses the zone's standard-time offset all year, ignoring daylight saving.
- **Why the naive grader missed it:** `account_tz='UTC'` has no daylight saving, so a fixed offset equals the zone.
- **Hardening:** final tests that fail this variant: `test_dst_months (Toronto March and November, Auckland April)`.
- **Superseded by v2:** F-106 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="08_refund_limits-starter-v1"></a>
### F-028 · 08_refund_limits · starter · false_pass under naive (v1, superseded)
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** The v1 starter (a cap on `authorized` minus refunded that also counted rejected attempts) passed the naive grader.
- **Why the naive grader missed it:** `test_single_full_refund` and `test_over_refund_rejected` use authorized == captured == 100, where authorized and captured limits coincide, and only one refund is made per payment.
- **Hardening:** final tests that fail this starter: `test_cumulative_partials`, `test_capture_less_than_authorization`, `test_valid_after_rejection`, `test_refund_sequence_matches_greedy_oracle`.
- **Superseded by v2:** F-107 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="08_refund_limits-wrong_checks_single_refund-v1"></a>
### F-029 · 08_refund_limits · wrong_checks_single_refund · false_pass under naive (v1, superseded)
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** Checks each refund against the captured amount, ignoring earlier refunds.
- **Why the naive grader missed it:** Each naive payment receives at most one refund, so a per-refund check and a cumulative check agree.
- **Hardening:** final tests that fail this variant: `test_cumulative_partials`, `test_refund_sequence_matches_greedy_oracle`.
- **Superseded by v2:** F-107 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="08_refund_limits-wrong_uses_authorized-v1"></a>
### F-030 · 08_refund_limits · wrong_uses_authorized · false_pass under naive (v1, superseded)
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** Uses the authorized amount as the ceiling instead of the captured amount.
- **Why the naive grader missed it:** Both naive payments capture exactly the authorized 100, so the two ceilings are equal.
- **Hardening:** final tests that fail this variant: `test_capture_less_than_authorization`, `test_refund_sequence_matches_greedy_oracle`.
- **Superseded by v2:** F-107 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="08_refund_limits-wrong_counts_rejected-v1"></a>
### F-031 · 08_refund_limits · wrong_counts_rejected · false_pass under naive (v1, superseded)
- **Naive grader commit:** a4adcfb · **Hardened commit:** 28e2a21
- **What slipped through:** Adds a rejected over-refund attempt to the refunded counter, falsely rejecting later valid refunds.
- **Why the naive grader missed it:** `test_over_refund_rejected` ends after the rejected 101 refund; it never makes a valid refund afterwards or reads `refunded_total`.
- **Hardening:** final tests that fail this variant: `test_valid_after_rejection`, `test_cumulative_partials`, `test_capture_less_than_authorization`.
- **Lesson:** Test the recovery after a rejection, not only the rejection.
- **Superseded by v2:** F-107 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="09_tiered_fees-starter-v1"></a>
### F-032 · 09_tiered_fees · starter · false_pass under naive (v1, superseded)
- **Naive grader commit:** f047a0b · **Hardened commit:** cfd4d2e
- **What slipped through:** The v1 starter (the reference without the clamp) passed the naive grader.
- **Why the naive grader missed it:** `test_tier_midpoints` builds its schedule with `min_fee_minor=0` and `max_fee_minor=999999`, so the clamp is never reached.
- **Hardening:** final tests that fail this starter: `test_clamps_and_zero`, `test_fee_properties`.
- **Superseded by v2:** F-104 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="09_tiered_fees-wrong_exclusive_boundary-v1"></a>
### F-033 · 09_tiered_fees · wrong_exclusive_boundary · false_pass under naive (v1, superseded)
- **Naive grader commit:** f047a0b · **Hardened commit:** cfd4d2e
- **What slipped through:** Selects tiers with an exclusive upper bound.
- **Why the naive grader missed it:** `test_tier_midpoints` uses 5000, 15000 and 30000, each in the middle of a tier; no amount sits on a bound.
- **Hardening:** final tests that fail this variant: `test_inclusive_boundaries`.
- **Lesson:** Boundary bugs need amounts at bound - 1, bound and bound + 1.
- **Superseded by v2:** F-104 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="09_tiered_fees-wrong_float_bps-v1"></a>
### F-034 · 09_tiered_fees · wrong_float_bps · false_pass under naive (v1, superseded)
- **Naive grader commit:** f047a0b · **Hardened commit:** cfd4d2e
- **What slipped through:** Applies bps with a float multiply; exact half-unit results round the wrong way.
- **Why the naive grader missed it:** The three naive fees (60, 95, 105) are exact integers before rounding, so no half-unit tie occurs.
- **Hardening:** final tests that fail this variant: `test_discovered_float_ties[5000-3-2]`, `test_discovered_float_ties[25000-3-8]`, `test_discovered_float_ties[35000-3-11]`.
- **Lesson:** Tie inputs have to be searched with an exact-arithmetic oracle (`tools/find_ties.py`).
- **Superseded by v2:** F-104 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="10_batch_parser-wrong_partial_accept-v1"></a>
### F-035 · 10_batch_parser · wrong_partial_accept · false_pass under naive (v1, superseded)
- **Naive grader commit:** 4b90fce · **Hardened commit:** 94c0302
- **What slipped through:** Accepts the valid details of a batch that also contains invalid detail records.
- **Why the naive grader missed it:** The only rejection test (`test_count_mismatch`) corrupts the trailer count, which this variant still rejects; no naive file contains an invalid detail line.
- **Hardening:** final tests that fail this variant: `test_atomic_batch_rejection`.
- **Superseded by v2:** F-105 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="10_batch_parser-wrong_ignores_hash_total-v1"></a>
### F-036 · 10_batch_parser · wrong_ignores_hash_total · false_pass under naive (v1, superseded)
- **Naive grader commit:** 4b90fce · **Hardened commit:** 94c0302
- **What slipped through:** Does not check the trailer hash total.
- **Why the naive grader missed it:** Every naive file carries a correct hash total and the one corrupted file changes only the count.
- **Hardening:** final tests that fail this variant: `test_hash_total`, `test_atomic_batch_rejection`, `test_multiple_errors_and_line_numbers`.
- **Superseded by v2:** F-105 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

<a id="10_batch_parser-wrong_crlf_slicing-v1"></a>
### F-037 · 10_batch_parser · wrong_crlf_slicing · false_pass under naive (v1, superseded)
- **Naive grader commit:** 4b90fce · **Hardened commit:** 94c0302
- **What slipped through:** Checks line width before stripping CR, so CRLF files fail.
- **Why the naive grader missed it:** The naive `render()` default is `crlf=False`; every naive file is LF-terminated.
- **Hardening:** final tests that fail this variant: `test_crlf`, `test_roundtrip_and_single_digit_corruption`.
- **Superseded by v2:** F-105 (the starter, variants or naive grader of this task were redesigned; this entry is the v1 record).

## v2 redesign (review R1)

Each F-1xx entry explains why the v1 starter was redesigned (citing the review and the measured
starter-to-reference diff), what the v2 starter lacks, the new wrong variants, the naive results with
the commit they were measured at, and the hardened commit. Predictions in task.toml were recorded
before each naive run; mismatches are called out.

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

<a id="10_batch_parser-v2"></a>
### F-105 · 10_batch_parser · v2 redesign
- **Why v1 was redesigned:** review R1. The v1 starter differed from the reference by 2 changed
  lines (`or count != declared_count`); it already stripped CRLF, validated headers and trailers,
  checked the hash total and rejected whole batches, so all three v1 wrongs (`wrong_partial_accept`,
  `wrong_ignores_hash_total`, `wrong_crlf_slicing`) were regressions. v1 entries for this task
  (including the "starter passed 9/9 final tests" finding, which concerned the v1 starter) are
  **superseded by v2**.
- **v2 starter:** interprets detail records only, splits the file on LF only, never looks at the
  header or trailer, and returns the valid payments of a batch whose other detail lines were
  malformed; plus error-description, summary and CSV support code (224 non-test lines).
  `ref_diff_lines` 2 -> 63 (floor 25). The alternative has an independent regex-based records module
  (alt distance 0.451; 0.736 while it shared the reference's records module).
- **v2 wrong variants:** `wrong_partial_accept` (keeps accepting the valid details of a batch with
  malformed details), `wrong_ignores_hash_total` (count and control total only), `wrong_crlf_slicing`
  (full validation, but the starter's LF-only line splitting). None is regressive.
- **Naive grader (commit fd8c3c3):** 3 tests: `test_valid_lf`, `test_ticket_worked_example` (the
  two-payment batch in PROBLEM.md, accepted), `test_count_mismatch`. All three wrongs are
  **false_pass**, as predicted: every accepted naive file is LF-terminated and internally consistent
  (so CRLF and the hash total are never exercised), and the only rejection test corrupts the trailer
  count, which all three wrongs still detect. The unmodified starter fails only `test_count_mismatch`.
- **Hardened commit:** fd8c3c3. The v1 final grader (10 tests incl. the round-trip property) needed
  no change; the starter fails 9 of 10.
```text
runs=12 final_ok=6/6 naive_false_pass=3 infra_errors=0 flips=0 wall_s=7.574
```

<a id="07_statement_periods-v2"></a>
### F-106 · 07_statement_periods · v2 redesign
- **Why v1 was redesigned:** review R1 (5 changed lines between starter and reference; the starter
  already shared the reference's structure and differed mainly in the zone object). The v1 starter
  (131 non-test lines) was also below the S1 floor once tests are excluded. v1 entries for this
  task are **superseded by v2**.
- **v2 starter:** every account's month is derived from UTC (`account_tz` is ignored), equal instants
  keep input order, and there is no time-zone, month or year validation; plus month arithmetic,
  rendering and a range preview (217 non-test lines). PROBLEM.md gained the validation rule and a
  Toronto worked example. `ref_diff_lines` 5 -> 27 (floor 25).
- **v2 wrong variants:** `wrong_utc_month` (validates, keeps UTC boundaries),
  `wrong_inclusive_2359` (zone-aware, period ends one second early), `wrong_fixed_offset`
  (standard-time offset all year). **One is regressive:** `wrong_inclusive_2359`, because the UTC
  starter already ends the period at the exclusive next-month start, so `test_microsecond_boundary`
  passes on the starter. The rationale is in task.toml and NOTES.md: moving to local time invites
  rewriting the end as the last second of the local month.
- **Naive grader (commit f030a1e):** 3 tests: `test_midmonth_utc`,
  `test_ticket_worked_example_toronto_january` (asserts the Toronto January bounds and that a
  23:30-local transaction is in January), `test_naive_timestamp_rejected`. `wrong_fixed_offset` is a
  **false_pass**: January is standard time in Toronto, so no ticket-example assertion separates a
  fixed standard offset from the real zone. `wrong_utc_month` was caught as predicted
  (`ok_wrong_reason`). **Prediction mismatch:** `wrong_inclusive_2359` was predicted false_pass but
  was also caught (`ok_wrong_reason`), because the worked example asserts the exact end instant
  returned by `period_bounds`, which that variant shifts by one second; `select` alone would not
  have caught it. The unmodified starter fails the worked example.
- **Hardened commit:** 35f0fc3, which adds `test_invalid_zone_month_or_year_raises` and
  `test_supported_year_range_edges` (the ticket validation rule); all variants stayed `ok` under final.
```text
runs=12 final_ok=6/6 naive_false_pass=1 infra_errors=0 flips=0 wall_s=9.912
```

<a id="08_refund_limits-v2"></a>
### F-107 · 08_refund_limits · v2 redesign
- **Why v1 was redesigned:** review R1 (10 changed lines between starter and reference; the v1
  starter already had a cumulative counter and an explicit write transaction, and differed mainly
  in using `authorized` instead of `captured` as the ceiling). v1 entries for this task, including
  the Windows `TemporaryDirectory` false_fail on the v1 reference (fb4e73e), are **superseded by v2**
  for the variants, but that fixture fix is kept (the final grader still collects connection cycles).
- **v2 starter:** records any refund of a captured payment with no limit, lets a payment be captured
  repeatedly, has no explicit write transaction and no unknown-id handling (AttributeError); plus
  store, CSV and report support code (221 non-test lines). PROBLEM.md gained the unknown-id rule and
  a worked example. `ref_diff_lines` 10 -> 42 (floor 25; the first attempt at the unknown-id rule alone
  reached 24, so the reference also gained a `store.immediate` transaction helper that always closes
  its connection, which the starter never did).
- **v2 wrong variants:** `wrong_checks_single_refund` (per-refund cap), `wrong_uses_authorized`
  (cap on authorized minus refunded), `wrong_counts_rejected` (adds a rejected attempt to the
  counter). None is regressive.
- **Naive grader (commit b8d844f):** 4 tests: `test_single_full_refund`, `test_over_refund_rejected`,
  `test_ticket_worked_example` (capture 6000, refund 4000, refund 2500 rejected, total still 4000),
  `test_refund_before_capture_rejected`. **All three wrongs were caught by the naive grader**
  (`ok_wrong_reason`, each failing `test_ticket_worked_example`): the ticket's own example
  already contains a cumulative over-refund, which defeats the per-refund and authorized-ceiling
  variants, and its closing `refunded_total == 4000` assertion exposes the counted rejection.
  Two predictions matched; **`wrong_counts_rejected` was predicted false_pass and was caught**
  (I had not accounted for the example's final assertion). The unmodified starter fails
  `test_over_refund_rejected` and `test_ticket_worked_example`.
- **Hardened commit:** 8195086. Final grader additions: `test_unknown_payment_id_raises_value_error`
  and `test_capture_once_and_within_authorization` (capture-once was only in the visible tests).
  All variants `ok` under final.
```text
runs=12 final_ok=6/6 naive_false_pass=0 infra_errors=0 flips=0 wall_s=64.444
```

<a id="01_idempotent_payments-v2"></a>
### F-108 · 01_idempotent_payments · v2 starter adjustment
- **Why:** review R1 floor check. The v1 starter was already a real feature gap (no idempotency at
  all) but `ref_diff_lines` was 33, below the hard floor of 40. This entry does **not** replace the
  v1 findings for this task; the wrong variants are unchanged in spirit.
- **Change:** the starter no longer contains the request fingerprint (`PaymentRequest.fingerprint`)
  or the `Idempotency-Key` length validation (`idempotency_key_required`); both are now part of the
  ticket. `ref_diff_lines` 33 -> 41. The reference and the three wrongs carry the reference
  `contracts.py`; the alternative performs the key check itself (alt distance 0.282). Reporting
  support code keeps the starter at 248 non-test lines.
- **Regressive variant:** `wrong_key_scope`. The starter has no keys, so it passes
  `test_same_key_different_merchants_independent` trivially; rationale recorded in task.toml and NOTES.md.
  The other two wrongs (`wrong_retry_race`, `wrong_inmemory_cache`) fail must_fail tests the starter fails.
- **Naive grader (commit bf30814):** unchanged, 3 tests: `test_create`, `test_retry` (the ticket's
  retry scenario, one merchant, sequential), `test_missing_key`. All three wrongs remain **false_pass**
  as predicted: the naive fixtures use one merchant, never restart the app and send duplicates
  sequentially. The starter now fails `test_retry` and `test_missing_key`.
- **Hardened commit:** bf30814 (final grader unchanged; starter fails 11 of 12 final tests).
```text
runs=12 final_ok=6/6 naive_false_pass=3 infra_errors=0 flips=0 wall_s=35.110
```

<a id="02_interest_accrual-v2"></a>
### F-109 · 02_interest_accrual · v2 starter and naive adjustment
- **Why:** review R2 and R4. The v1 starter was already a real feature gap (a float whole-month
  implementation, `ref_diff_lines` 38 >= 25) and its wrong variants were not redesigned, but it had
  only 147 non-test lines (S1 floor 200) and a one-test naive grader. This entry does **not**
  replace the v1 findings for this task.
- **Change:** report and CSV support modules (starter 213 non-test lines); a worked example in
  PROBLEM.md (1000.00 at 0.0365 from 2026-01-01 to 2026-03-01: 3.10 / 1003.10 then 2.81 / 1005.91, same
  for both methods); naive grader expanded to three tests, still tolerance-based (`abs(diff) <= 0.01`,
  any numeric type): `test_examples`, `test_ticket_worked_example[simple_monthly|daily_compound]`,
  `test_empty_period_and_reversed_dates`.
- **Regressive variant:** `wrong_round_daily`. The float starter never rounds daily, so it passes
  `test_small_balance_daily_accrues`; rationale in task.toml and NOTES.md.
- **Naive grader (commit 5f8b094):** all three wrongs remain **false_pass**, as predicted. The
  worked example is within one cent for float arithmetic, half-up and per-day rounding (3.1048...
  rounds to 3.10 and 2.8087... to 2.81 under every one of them), and no naive input is a half-cent tie
  or a large principal. The **unmodified float starter also passes the naive grader 4/4**
  (`false_pass`): its error on every naive input is below the 0.01 tolerance.
- **Hardened commit:** 5f8b094 (final grader unchanged; the starter fails 7 of 8 final tests).
```text
runs=12 final_ok=6/6 naive_false_pass=4 infra_errors=0 flips=0 wall_s=14.767
```

<a id="03_fx_quotes-v2"></a>
### F-110 · 03_fx_quotes · v2 redesign
- **Why v1 was redesigned:** review R1 (check) and R2. The v1 starter already used per-currency
  minor units, the USD cross route and exact `Decimal` rounding, and differed from the reference by
  28 changed lines that were mostly the fee deduction and a precision context; `wrong_two_decimals`
  and `wrong_round_cross_leg` described code the starter already got right (the `regressive_wrong`
  metric did not flag them only because their declared tests also exercise the fee). v1 entries for
  this task are **superseded by v2**. The v1 starter had 158 non-test lines.
- **v2 starter:** direct pairs only, a universal two-decimal scale, the fee computed but not
  deducted, no cross route; plus batch and report support code (212 non-test lines).
  `ref_diff_lines` 28 -> 25 (floor 25): the reference is short, and the smaller starter removed
  shared lines, so the margin is thin. PROBLEM.md gained a cross-quote and a JPY worked example.
- **v2 wrong variants:** `wrong_two_decimals` (cross route and fee deduction added, universal scale
  kept), `wrong_round_cross_leg` (USD leg rounded to cents), `wrong_fee_after_conversion` (gross
  conversion, destination-side fee). None is regressive.
- **Naive grader (commit 6c57023):** 4 tests: `test_direct_cad_usd`, `test_ticket_example_cross_quote`
  (GBP to CAD via USD, exact two-decimal arithmetic), `test_ticket_example_zero_decimal_currency`
  (CAD to JPY), `test_unknown_route_rejected`. `wrong_two_decimals` is **caught**
  (`ok_wrong_reason`: it fails the JPY example, not the declared `test_jpy_and_kwd_units`), as
  predicted. `wrong_round_cross_leg` and `wrong_fee_after_conversion` are **false_pass**: the cross
  example's USD leg (199.00 x 1.25 = 248.75) is already exact to cents, and fee-after-conversion is
  algebraically identical to fee-before-conversion whenever no rounding occurs, so no ticket
  example separates them. The unmodified starter fails three of four naive tests.
- **Hardened commit:** 6c57023 (final grader unchanged; the starter fails 4 of 9 final tests).
```text
runs=12 final_ok=6/6 naive_false_pass=2 infra_errors=0 flips=0 wall_s=10.258
```

<a id="02_interest_accrual-starter"></a>
### F-201 · 02_interest_accrual · starter · false_pass under naive
- **Naive grader commit:** 5f8b094 · **Hardened commit:** 5f8b094 (final grader unchanged since d86532e)
- **What slipped through:** The unmodified float starter passed all four naive tests.
- **Why the naive grader missed it:** `test_examples`, `test_ticket_worked_example[simple_monthly|daily_compound]` and `test_empty_period_and_reversed_dates` compare with `abs(diff) <= 0.01` (or test an empty list and a `ValueError`), and float arithmetic is accurate to ~1e-9 on 1000 to 5000 CAD over 31 to 59 days. The starter already validates dates, so the edge-case test passes too.
- **Hardening:** final tests that fail this starter: `test_half_cent_ties_bankers (3 cases)`, `test_large_principal_exact (both methods)`, `test_leap_and_partial`, `test_accrual_properties`.
- **Lesson:** A tolerance-based naive grader cannot reject an implementation whose error is below the tolerance, even when the implementation is a different arithmetic type.

<a id="02_interest_accrual-wrong_float"></a>
### F-202 · 02_interest_accrual · wrong_float · false_pass under naive
- **Naive grader commit:** 5f8b094 · **Hardened commit:** 5f8b094 (final grader unchanged since d86532e)
- **What slipped through:** Float arithmetic with `round(x, 2)`.
- **Why the naive grader missed it:** Same tolerance as above; the worked example's 3.1048 and 2.8087 are nowhere near a half-cent, and no naive principal exceeds 5000.
- **Hardening:** final tests that fail this variant: `test_half_cent_ties_bankers (3 cases)`.

<a id="02_interest_accrual-wrong_half_up"></a>
### F-203 · 02_interest_accrual · wrong_half_up · false_pass under naive
- **Naive grader commit:** 5f8b094 · **Hardened commit:** 5f8b094 (final grader unchanged since d86532e)
- **What slipped through:** `ROUND_HALF_UP` instead of half-even.
- **Why the naive grader missed it:** None of the naive results (3.10, 6.20, 15.50, 3.10, 2.81, 2.81) is an exact tie, so the rounding mode is not consulted; the tolerance would absorb a one-cent difference anyway.
- **Hardening:** final tests that fail this variant: `test_half_cent_ties_bankers (3 cases)`.

<a id="02_interest_accrual-wrong_round_daily"></a>
### F-204 · 02_interest_accrual · wrong_round_daily · false_pass under naive
- **Naive grader commit:** 5f8b094 · **Hardened commit:** 5f8b094 (final grader unchanged since d86532e)
- **What slipped through:** Rounds each day's accrual to cents.
- **Why the naive grader missed it:** The naive daily accruals (0.10, 0.20, 0.50, and 0.1000 compounding to 0.10001 in the worked example) are whole cents or round to the same cent, and the compound total's drift (3.10 against 3.1048) is inside the 0.01 tolerance.
- **Hardening:** final tests that fail this variant: `test_small_balance_daily_accrues`, `test_large_principal_exact (both methods)`.
- **Lesson:** Regressive by `check_realism`; see the rationale in task.toml.

<a id="03_fx_quotes-wrong_two_decimals"></a>
### F-205 · 03_fx_quotes · wrong_two_decimals · ok_wrong_reason under naive
- **Naive grader commit:** 6c57023 · **Hardened commit:** 6c57023 (final grader unchanged)
- **What slipped through:** Universal two-decimal scale kept from the starter.
- **Why the naive grader did not miss it:** Not missed: `test_ticket_example_zero_decimal_currency` (5000 CAD at 110 gives 5500 JPY) fails because this variant returns 550000. It is recorded as `ok_wrong_reason` because the declared must_fail test is `test_jpy_and_kwd_units`.
- **Hardening:** final tests that fail this variant: `test_jpy_and_kwd_units`, `test_exact_scaling_and_monotonicity`.
- **Lesson:** When the ticket's own example uses a non-default currency, the naive grader inherits the check.

<a id="03_fx_quotes-wrong_round_cross_leg"></a>
### F-206 · 03_fx_quotes · wrong_round_cross_leg · false_pass under naive
- **Naive grader commit:** 6c57023 · **Hardened commit:** 6c57023 (final grader unchanged)
- **What slipped through:** Rounds the USD leg of a cross quote to cents.
- **Why the naive grader missed it:** `test_ticket_example_cross_quote` (GBP to CAD via USD) has 199.00 x 1.25 = 248.75 USD, already exact to cents, so the rounding is a no-op.
- **Hardening:** final tests that fail this variant: `test_cross_has_no_intermediate_rounding`.
- **Lesson:** A worked example chosen for readable numbers is exactly the input on which intermediate rounding disappears.

<a id="03_fx_quotes-wrong_fee_after_conversion"></a>
### F-207 · 03_fx_quotes · wrong_fee_after_conversion · false_pass under naive
- **Naive grader commit:** 6c57023 · **Hardened commit:** 6c57023 (final grader unchanged)
- **What slipped through:** Converts the gross amount and subtracts a destination-side fee.
- **Why the naive grader missed it:** Fee-before and fee-after are algebraically the same when nothing is rounded; the cross example (fee 100 of 20000, 34825 either way) and the zero-fee JPY example contain no rounding between the two orders.
- **Hardening:** final tests that fail this variant: `test_source_fee_before_conversion`, `test_jpy_and_kwd_units`.

<a id="04_ledger_reconciliation-wrong_no_consumption"></a>
### F-208 · 04_ledger_reconciliation · wrong_no_consumption · false_pass under naive
- **Naive grader commit:** e1b318e · **Hardened commit:** e1b318e (final grader unchanged)
- **What slipped through:** Keeps the starter's non-consuming candidate lookup, so one ledger entry can match several statement lines.
- **Why the naive grader missed it:** `test_clean_one_to_one` and `test_ticket_worked_example` give every statement line its own ledger entry and assert `len(matches)` (3 and 2); a variant that never marks entries used returns the same counts.
- **Hardening:** final tests that fail this variant: `test_duplicate_statement_line_left_unmatched`, `test_ground_truth_transforms`.
- **Lesson:** Count assertions hide identity reuse.

<a id="04_ledger_reconciliation-wrong_split_ignored"></a>
### F-209 · 04_ledger_reconciliation · wrong_split_ignored · ok_wrong_reason under naive
- **Naive grader commit:** e1b318e · **Hardened commit:** e1b318e (final grader unchanged)
- **What slipped through:** Implements everything except the R2 split rule.
- **Why the naive grader did not miss it:** Not missed: the ticket's worked example contains a split, and `test_ticket_worked_example` asserts `len(result.matches) == 2` and no unmatched lines; without R2 only one match is found. Recorded as `ok_wrong_reason` because the declared test is `test_split_all_lines`.
- **Hardening:** final tests that fail this variant: `test_split_all_lines`, `test_ground_truth_transforms`.

<a id="04_ledger_reconciliation-wrong_refund_abs"></a>
### F-210 · 04_ledger_reconciliation · wrong_refund_abs · false_pass under naive
- **Naive grader commit:** e1b318e · **Hardened commit:** e1b318e (final grader unchanged)
- **What slipped through:** Compares `abs(amount)` in the exact rule, so a refund line can match a payment.
- **Why the naive grader missed it:** No naive statement line is negative; `abs()` is the identity on every naive input.
- **Hardening:** final tests that fail this variant: `test_refund_kind_and_original_reference`.

<a id="05_double_entry-wrong_cross_currency_sum"></a>
### F-211 · 05_double_entry · wrong_cross_currency_sum · false_pass under naive
- **Naive grader commit:** 72eacbc · **Hardened commit:** 72eacbc (final grader unchanged)
- **What slipped through:** Balances one grand total across currencies.
- **Why the naive grader missed it:** `accounts()` creates both naive accounts in CAD, and the ticket example is CAD only, so the grand total equals the per-currency total.
- **Hardening:** final tests that fail this variant: `test_cross_currency_cannot_net`, `TestJournal (stateful machine)`.
- **Lesson:** A single-currency fixture cannot test a per-currency invariant.

<a id="05_double_entry-wrong_non_atomic"></a>
### F-212 · 05_double_entry · wrong_non_atomic · false_pass under naive
- **Naive grader commit:** 72eacbc · **Hardened commit:** 72eacbc (final grader unchanged)
- **What slipped through:** Keeps the starter's autocommit connection and validates while inserting.
- **Why the naive grader missed it:** `test_unbalanced_rejected` asserts only `pytest.raises(UnbalancedTransaction)`; it reads no balance afterwards. No naive post uses an unknown account.
- **Hardening:** final tests that fail this variant: `test_unknown_account_is_atomic`, `test_rejections_leave_no_trace`, `test_cross_currency_cannot_net`.
- **Lesson:** Read state after a rejection.

<a id="05_double_entry-wrong_double_reverse"></a>
### F-213 · 05_double_entry · wrong_double_reverse · false_pass under naive
- **Naive grader commit:** 72eacbc · **Hardened commit:** 72eacbc (final grader unchanged)
- **What slipped through:** Reversal without the once-only check.
- **Why the naive grader missed it:** `test_ticket_example_post_then_reverse` reverses once and asserts balances; no naive test reverses a transaction a second time.
- **Hardening:** final tests that fail this variant: `test_reverse_once`, `TestJournal (stateful machine)`.

<a id="06_available_balance-wrong_available_ignores_holds"></a>
### F-214 · 06_available_balance · wrong_available_ignores_holds · ok_wrong_reason under naive
- **Naive grader commit:** 4c7bb1c · **Hardened commit:** 4c7bb1c (final grader unchanged)
- **What slipped through:** Capture, void and expiry added; the starter's `available == posted` kept.
- **Why the naive grader did not miss it:** Not missed: `test_ticket_worked_example` asserts `available_minor == 7000` right after authorizing 3000; this variant reports 10000. Recorded as `ok_wrong_reason` because the declared test is `test_existing_holds_reduce_available`.
- **Hardening:** final tests that fail this variant: `test_existing_holds_reduce_available`, `test_overdraft_boundary`, `test_random_operation_model`.

<a id="06_available_balance-wrong_partial_capture_keeps_remainder"></a>
### F-215 · 06_available_balance · wrong_partial_capture_keeps_remainder · ok_wrong_reason under naive
- **Naive grader commit:** 4c7bb1c · **Hardened commit:** 4c7bb1c (final grader unchanged)
- **What slipped through:** Leaves the unused part of a partially captured hold active.
- **Why the naive grader did not miss it:** Not missed: after capturing 1200 of 3000, `test_ticket_worked_example` asserts `available_minor == 8800`; this variant leaves 1800 held and reports 7000.
- **Hardening:** final tests that fail this variant: `test_partial_capture_releases_remainder`, `test_random_operation_model`.

<a id="06_available_balance-wrong_expired_holds_count"></a>
### F-216 · 06_available_balance · wrong_expired_holds_count · false_pass under naive
- **Naive grader commit:** 4c7bb1c · **Hardened commit:** 4c7bb1c (final grader unchanged)
- **What slipped through:** Counts holds without the 7-day expiry cut-off.
- **Why the naive grader missed it:** The naive `Clock` is fixed at 2026-01-01T00:00Z; `test_full_capture`, `test_ticket_worked_example` and `test_invalid_amount_rejected` never advance it, so no hold ever ages.
- **Hardening:** final tests that fail this variant: `test_expiry_exactly_seven_days`, `test_random_operation_model`.
- **Lesson:** Time rules need a clock the test can move.

<a id="07_statement_periods-wrong_utc_month"></a>
### F-217 · 07_statement_periods · wrong_utc_month · ok_wrong_reason under naive
- **Naive grader commit:** f030a1e · **Hardened commit:** 35f0fc3
- **What slipped through:** Validates the zone but keeps UTC month boundaries.
- **Why the naive grader did not miss it:** Not missed: `test_ticket_worked_example_toronto_january` asserts the Toronto bounds (05:00Z) and that a transaction at 04:30Z on 1 February belongs to January. Recorded as `ok_wrong_reason` because the declared test is `test_local_midnight_boundaries`.
- **Hardening:** final tests that fail this variant: `test_local_midnight_boundaries (Toronto, Kolkata)`, `test_dst_months (3 zones)`.

<a id="07_statement_periods-wrong_inclusive_2359"></a>
### F-218 · 07_statement_periods · wrong_inclusive_2359 · ok_wrong_reason under naive
- **Naive grader commit:** f030a1e · **Hardened commit:** 35f0fc3
- **What slipped through:** Zone-aware, but the period ends one second before local midnight.
- **Why the naive grader did not miss it:** **Prediction mismatch** (predicted false_pass). `test_ticket_worked_example_toronto_january` asserts `period_bounds(...)[1] == 2026-02-01T05:00Z`; this variant returns 04:59:59Z. A naive grader that only called `select` would not have caught it.
- **Hardening:** final tests that fail this variant: `test_microsecond_boundary`, `test_local_midnight_boundaries`, `test_thirteen_month_partition`.
- **Lesson:** Asserting the returned bounds, not only the selection, catches off-by-one-second ends. This variant is regressive by `check_realism` (rationale in task.toml).

<a id="07_statement_periods-wrong_fixed_offset"></a>
### F-219 · 07_statement_periods · wrong_fixed_offset · false_pass under naive
- **Naive grader commit:** f030a1e · **Hardened commit:** 35f0fc3
- **What slipped through:** Uses the zone's standard-time offset all year.
- **Why the naive grader missed it:** The ticket example is January, when Toronto is on standard time, so a fixed standard offset equals the real zone; no naive input is in a daylight-saving month.
- **Hardening:** final tests that fail this variant: `test_dst_months (Toronto March and November, Auckland April)`.
- **Lesson:** A winter example cannot see a daylight-saving bug.

<a id="08_refund_limits-wrong_checks_single_refund"></a>
### F-220 · 08_refund_limits · wrong_checks_single_refund · ok_wrong_reason under naive
- **Naive grader commit:** b8d844f · **Hardened commit:** 8195086
- **What slipped through:** Caps each refund at the captured amount, not the running total.
- **Why the naive grader did not miss it:** Not missed: `test_ticket_worked_example` refunds 4000 then 2500 against a capture of 6000; the variant accepts 2500 (it is below 6000) and the expected `RefundExceedsCaptured` is not raised.
- **Hardening:** final tests that fail this variant: `test_cumulative_partials`, `test_refund_sequence_matches_greedy_oracle`.

<a id="08_refund_limits-wrong_uses_authorized"></a>
### F-221 · 08_refund_limits · wrong_uses_authorized · ok_wrong_reason under naive
- **Naive grader commit:** b8d844f · **Hardened commit:** 8195086
- **What slipped through:** Caps the running total at authorized (10000) minus refunded instead of captured (6000).
- **Why the naive grader did not miss it:** Not missed: in `test_ticket_worked_example` the second refund of 2500 is below 10000 - 4000, so the variant accepts it.
- **Hardening:** final tests that fail this variant: `test_capture_less_than_authorization`, `test_refund_sequence_matches_greedy_oracle`.

<a id="08_refund_limits-wrong_counts_rejected"></a>
### F-222 · 08_refund_limits · wrong_counts_rejected · ok_wrong_reason under naive
- **Naive grader commit:** b8d844f · **Hardened commit:** 8195086
- **What slipped through:** Adds a rejected attempt to the refunded counter.
- **Why the naive grader did not miss it:** **Prediction mismatch** (predicted false_pass). The ticket example's last line asserts `refunded_total(p) == 4000` after the rejected 2500 refund; this variant reports 6500. The assertion is a state check after a rejection, the pattern the final grader uses elsewhere.
- **Hardening:** final tests that fail this variant: `test_valid_after_rejection`, `test_cumulative_partials`, `test_capture_less_than_authorization`.
- **Lesson:** Reading state after a rejection catches counted rejections even when no valid refund follows.

<a id="09_tiered_fees-wrong_exclusive_boundary"></a>
### F-223 · 09_tiered_fees · wrong_exclusive_boundary · false_pass under naive
- **Naive grader commit:** e0e65b9 · **Hardened commit:** 68ae615
- **What slipped through:** Tier selection with `<` instead of `<=`.
- **Why the naive grader missed it:** `test_tier_midpoints` and `test_ticket_worked_example_with_clamps` use 100, 5000, 15000 and 30000, none within one unit of a bound (10000, 20000).
- **Hardening:** final tests that fail this variant: `test_inclusive_boundaries`.
- **Lesson:** Boundary bugs need amounts at bound - 1, bound and bound + 1.

<a id="09_tiered_fees-wrong_float_bps"></a>
### F-224 · 09_tiered_fees · wrong_float_bps · false_pass under naive
- **Naive grader commit:** e0e65b9 · **Hardened commit:** 68ae615
- **What slipped through:** Half-up via a float percentage.
- **Why the naive grader missed it:** Every naive raw fee (11, 60, 95, 105) is an integer before rounding, so there is no half-unit tie for float error to flip.
- **Hardening:** final tests that fail this variant: `test_discovered_float_ties[5000-3-2]`, `test_discovered_float_ties[25000-3-8]`, `test_discovered_float_ties[35000-3-11]`.
- **Lesson:** Tie inputs have to be searched with an exact-arithmetic oracle.

<a id="09_tiered_fees-wrong_marginal"></a>
### F-225 · 09_tiered_fees · wrong_marginal · ok_wrong_reason under naive
- **Naive grader commit:** e0e65b9 · **Hardened commit:** 68ae615
- **What slipped through:** Prices each band separately.
- **Why the naive grader did not miss it:** Not missed: `test_tier_midpoints` expects 95 for 15000 (non-marginal) and the variant returns 145; `test_ticket_worked_example_with_clamps` fails the same way.
- **Hardening:** final tests that fail this variant: `test_inclusive_boundaries`, `test_non_marginal`.

<a id="10_batch_parser-wrong_partial_accept"></a>
### F-226 · 10_batch_parser · wrong_partial_accept · false_pass under naive
- **Naive grader commit:** fd8c3c3 · **Hardened commit:** fd8c3c3 (final grader unchanged)
- **What slipped through:** Keeps accepting the valid details of a batch with malformed details.
- **Why the naive grader missed it:** The only naive rejection is `test_count_mismatch`, which corrupts the trailer count (still rejected by this variant); no naive file contains an invalid detail line.
- **Hardening:** final tests that fail this variant: `test_atomic_batch_rejection`.

<a id="10_batch_parser-wrong_ignores_hash_total"></a>
### F-227 · 10_batch_parser · wrong_ignores_hash_total · false_pass under naive
- **Naive grader commit:** fd8c3c3 · **Hardened commit:** fd8c3c3 (final grader unchanged)
- **What slipped through:** Checks count and control total but not the hash total.
- **Why the naive grader missed it:** Every naive file, including the worked example (hash 80235), has a correct hash total; `test_count_mismatch` corrupts only the count.
- **Hardening:** final tests that fail this variant: `test_hash_total`, `test_atomic_batch_rejection`, `test_multiple_errors_and_line_numbers`.

<a id="10_batch_parser-wrong_crlf_slicing"></a>
### F-228 · 10_batch_parser · wrong_crlf_slicing · false_pass under naive
- **Naive grader commit:** fd8c3c3 · **Hardened commit:** fd8c3c3 (final grader unchanged)
- **What slipped through:** Keeps the starter's LF-only line splitting, so CRLF files fail.
- **Why the naive grader missed it:** The naive `render()` helper produces LF-terminated files only (rows are joined with LF only), and no naive test builds a CRLF file.
- **Hardening:** final tests that fail this variant: `test_crlf`, `test_roundtrip_and_single_digit_corruption`.
- **Lesson:** A fixture helper that cannot produce the awkward variant (CRLF) guarantees the awkward variant is never tested.


## Patterns

Data: v2 matrix, `results/final/matrix.json`. Naive graders now have 3 to 4 tests each, including the ticket's own
worked example. **20 of the 30 wrong variants still pass the naive graders** (v1: 29 of 30), **1 of 10 unmodified
starters** passes (v1: 5 of 10), 10 wrong variants are caught by the naive grader, and 0 of 20 valid solutions are
rejected. All 10 caught variants are caught by an assertion taken from the ticket's example, never by a test that
the declared `must_fail` names. Predictions recorded before the naive runs matched 28 of 30 wrong variants (mismatches:
F-218 and F-222, both caught when I predicted a false pass).

1. **State over time is invisible to one-shot examples.** 01 `wrong_retry_race`, 01 `wrong_inmemory_cache`,
   05 `wrong_double_reverse` and 06 `wrong_expired_holds_count` all pass the v2 naive graders. Their naive fixtures send
   one request at a time, build one app instance, reverse a transaction once and use a clock that never moves. The
   hardened graders needed simultaneous duplicates behind a barrier, a second app instance, a repeated reversal and a
   movable clock. The counter-example is task 08: all three variants are caught because the ticket's example is itself
   a two-step sequence (refund 4000, then 2500) followed by a read of `refunded_total`.
2. **Numeric bugs live on measure-zero inputs.** 02 `wrong_half_up` and `wrong_float` (tolerance 0.01),
   03 `wrong_round_cross_leg` (the readable example 199.00 x 1.25 = 248.75 is exact), 09 `wrong_float_bps` and
   `wrong_exclusive_boundary` (no amount near a bound or a tie) and 07 `wrong_fixed_offset` (a January example cannot see
   daylight saving) pass the naive graders. The fix is searched tie and boundary inputs (`tools/find_ties.py`) checked
   by exact Fraction arithmetic (`tools/verify_cases.py`), exact type and exponent assertions, and examples in a
   daylight-saving month. A worked example that uses a non-default currency (03 JPY) or a non-UTC zone (07 Toronto)
   does catch the variants built on the default; 07 `wrong_inclusive_2359` is caught only because the example asserts the
   exact bounds returned by `period_bounds`, not just the selection.
3. **Counts and totals hide identity and scope bugs.** 04 `wrong_no_consumption` and `wrong_refund_abs`,
   01 `wrong_key_scope` and 05 `wrong_cross_currency_sum` pass the naive graders: `len(matches)`, one merchant and one
   currency give the same numbers with the wrong pairing, namespace or base. Asserting the set of id pairs, results per
   scope and per-currency invariants catches them.
4. **Rejection paths need state assertions, not just error assertions.** 05 `wrong_non_atomic` raises the right error but
   leaves lines behind; 10 `wrong_partial_accept` is rejected for a corrupt trailer count but not for a bad detail line.
   08 `wrong_counts_rejected` is the exception that proves it: it is caught only because the example's last line reads
   `refunded_total` after the rejection. Every hardened grader checks observable state (trial balance, payments, the next
   valid refund) after each rejected operation.
5. **Hardening itself regresses, and redesign exposes untested requirements.** In v1 the first hardened grader for task 10
   dropped the naive count-mismatch test, so the starter passed 9/9 final tests (F-001), and graders for 05 and 08 first
   produced false fails on valid code (F-002, F-003). In v2, moving schedule validation (09), zone and month validation (07)
   and unknown-id handling (08) from visible tests or constructors into the ticket showed that the v1 final graders had no
   hidden test for them; each needed a new hardened test (F-104, F-106, F-107). A requirement enforced only by visible tests
   is silently ungraded.
6. **The ticket's example calibrates the naive grader.** Adding the worked example and a validation case lowered the
   naive false-pass rate from 29/30 to 20/30; which variants survive depends on what the example happens to contain
   (a winter date, an exact cross leg, a sequence of two refunds). The remaining false passes are the ones whose
   distinguishing input is a restart, a clock change, a tie, a bound, a second currency or a second merchant.
7. **The starter's shape decides which wrong variants are plausible.** The v1 starters for 04, 05, 06, 09 and 10 were
   the reference minus one line (2 to 5 changed lines); 17 of 30 wrong variants failed final tests the starter passed. In
   v2 `ref_diff_lines` is 25 to 64 and `regressive_wrong` flags 3 of 30 variants (01 `wrong_key_scope`, 02
   `wrong_round_daily`, 07 `wrong_inclusive_2359`), each with a logged rationale.

## Limitations

- Every task, solution and grader was written by one author. The wrong variants
  are the bugs that author predicted; real model failures may cluster differently (the M5 stretch goal was not run).
- The same author wrote the ticket examples that now drive the naive graders, and knew the wrong variants when writing
  them. Predictions were recorded before each naive run (28 of 30 matched), but 20/30 is a property of these examples, not an
  estimate of what a hurried human author would let through.
- The three regressive variants (F-108, F-109, F-218) rest on rationales a reviewer must accept. `ref_diff_lines` for task 03
  sits exactly on its floor (25).
- The blind reviews (S5) are disciplined self-reviews, not independent reviews. An independent review is still owed.
- Verified natively on Windows 11 with Python 3.14 and PostgreSQL 16.13. The Docker path (Python 3.12 image) was written
  but not executed, so S4 is unmeasured. The requirements lock is verified against installed-package metadata
  (`tools/check_lock.py`) and the code against `ruff --target-version py312`, not against a Python 3.12 interpreter.
- The Harbor export follows only documented task.toml keys. Mount paths and compose conventions are labeled assumptions,
  validated by a local simulation rather than the Harbor runtime. Agent timeout and resource limits are chosen values.
- Isolation is for reproducibility, not for hostile code. Candidate code runs as the same user.

## Implications for task authoring at scale

- Run the unmodified starter and a structurally different valid solution through every grader version. Both caught grader
  defects here (a dropped regression, an overfitted fixture) that reference-only checks would have missed.
- Measure the starter-to-reference diff and, for every wrong variant, whether the starter already fails the test the variant
  is declared to fail. A starter that is the reference minus one line turns the task into a bug hunt and makes the wrong
  variants regressions; the fix is a starter in which the ticket's feature is genuinely missing.
- Derive the naive grader from the ticket's own example plus one validation case, record predictions first, and read the
  mismatches: they show where the example, not the grader, did the work.
- For numeric tasks, require searched tie and boundary inputs with an exact-arithmetic oracle. Hand-picked examples nearly
  never land on the inputs that separate correct from plausible code.
- Require at least one stateful test (sequence, restart, clock or concurrency) for any task whose ticket mentions
  persistence, retries, limits or lifecycle, and audit that every requirement in the ticket has a hidden test.
- Treat "fails for the declared reason" (`must_fail`) as part of grader QA. A wrong solution that fails for an incidental
  reason is a latent false pass for the next variant.
