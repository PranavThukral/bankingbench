# Ticket: enforce the journal invariant

`ledger.service.LedgerService(database_url)` operates a synthetic PostgreSQL ledger.
Expose frozen `Line(account_code: str, side: "debit"|"credit", amount_minor: int)` and:
`create_account(code,currency)`, `post(lines: list[Line],memo: str)->int`,
`reverse(txn_id:int,memo:str)->int`, `balance(account_code)->int`,
`trial_balance()->dict[str,tuple[int,int]]`.

Money uses integer minor units. Currencies: CAD/USD/EUR/GBP=2 dp, JPY=0, KWD/BHD=3;
no exchange or cross-currency netting. Errors derive from LedgerError:
UnbalancedTransaction, InvalidAmount, UnknownAccount, AlreadyReversed, CannotReverseReversal.

- A post has at least two lines (otherwise UnbalancedTransaction). Each amount is a positive
  int, never bool (otherwise InvalidAmount). Side must be debit or credit (LedgerError).
- All accounts must exist (UnknownAccount). For EACH currency independently, sum of debits
  equals sum of credits (otherwise UnbalancedTransaction).
- Posting is atomic. Every rejected operation leaves balances and trial balance unchanged,
  including a missing account after other valid lines. Inputs are not mutated.
- Balance is debits minus credits. trial_balance keys are all currencies of created accounts,
  values are `(total_debits,total_credits)` across all posted lines, including reversal lines.
  A currency without postings has `(0,0)`. balance of an unknown account raises UnknownAccount.
- reverse creates a new transaction, with every side swapped, links it to the original and
  returns its distinct id. An original can be reversed at most once (AlreadyReversed).
  A reversal itself cannot be reversed (CannotReverseReversal). An unknown txn raises LedgerError.
  Reversal counts as real debit/credit turnover; it does not erase original lines.
- State survives constructing a new service. Re-creating an account with the same code and
  currency is idempotent; different currency, empty code or unsupported currency -> LedgerError.
- Validation priority: line count, amount/side, accounts, balancing. On reversing a reversal,
  CannotReverseReversal takes priority. Memo is arbitrary synthetic text.

Worked example (CAD accounts `cash` and `revenue`, synthetic):
`post([Line("cash","debit",5000), Line("revenue","credit",5000)], "sale")` returns id 1;
afterwards `balance("cash") == 5000`, `balance("revenue") == -5000` and `trial_balance()["CAD"] == (5000, 5000)`.
`reverse(1, "undo sale")` returns a different id; both balances are then 0 and the CAD trial balance is
`(10000, 10000)`. Reversing id 1 again raises AlreadyReversed.

The service may create its own tables; tests observe only the declared methods. Run
`python -m pytest tests -q` from starter with DATABASE_URL pointing at a disposable database.
