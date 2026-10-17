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
