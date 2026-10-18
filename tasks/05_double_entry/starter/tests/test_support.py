import os
from uuid import uuid4
from ledger.format import format_minor, render_trial_balance, render_posting
from ledger.importer import read_entries, book_all
from ledger.models import Line
from ledger.service import LedgerService


def two_accounts():
    service = LedgerService(os.environ["DATABASE_URL"])
    a, b = "a" + uuid4().hex, "b" + uuid4().hex
    service.create_account(a, "CAD")
    service.create_account(b, "CAD")
    return service, a, b


def test_format_minor_uses_currency_places():
    assert format_minor(12345, "CAD") == "123.45 CAD"
    assert format_minor(-5, "USD") == "-0.05 USD"
    assert format_minor(500, "JPY") == "500 JPY"
    assert format_minor(1234, "KWD") == "1.234 KWD"


def test_render_trial_balance_and_posting():
    text = render_trial_balance({"CAD": (300, 100), "JPY": (5, 5)})
    assert "CAD" in text and "2.00 CAD" in text and "JPY" in text
    entry = render_posting([Line("cash", "debit", 250)], {"cash": "CAD"}, "deposit")
    assert entry.startswith("Entry: deposit") and "2.50 CAD" in entry


def test_import_groups_rows_and_books_valid_entries(tmp_path):
    service, a, b = two_accounts()
    path = tmp_path / "journal.csv"
    path.write_text("entry,memo,account_code,side,amount_minor\n"
                    f"e1,first,{a},debit,100\ne1,first,{b},credit,100\n", encoding="utf-8")
    entries = read_entries(path)
    assert [(key, memo, len(lines)) for key, memo, lines in entries] == [("e1", "first", 2)]
    booked, rejected = book_all(service, entries)
    assert set(booked) == {"e1"} and rejected == {}
    assert service.balance(a) == 100


def test_import_reports_a_rejected_entry_without_stopping(tmp_path):
    service, a, b = two_accounts()
    path = tmp_path / "journal.csv"
    path.write_text("entry,memo,account_code,side,amount_minor\n"
                    f"bad,one-sided,{a},debit,100\n"
                    f"good,balanced,{a},debit,5\ngood,balanced,{b},credit,5\n", encoding="utf-8")
    booked, rejected = book_all(service, read_entries(path))
    assert set(booked) == {"good"} and set(rejected) == {"bad"}
