from datetime import datetime, timezone
import json
import pytest
from statements.models import Txn, PeriodRequest, Selection
from statements.months import parse_month, format_month, next_month, previous_month, iter_months
from statements.preview import main, preview_range
from statements.render import local_text, render_selection


def test_month_arithmetic():
    assert parse_month("2026-03") == (2026, 3)
    assert next_month(2026, 12) == (2027, 1) and previous_month(2026, 1) == (2025, 12)
    assert format_month(2026, 3) == "2026-03"
    assert list(iter_months((2026, 11), (2027, 2))) == [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]
    assert list(iter_months((2026, 3), (2026, 2))) == []


@pytest.mark.parametrize("text", ["2026", "2026-13", "2026-xx", "2026-1-1"])
def test_parse_month_rejects_bad_text(text):
    with pytest.raises(ValueError):
        parse_month(text)


def test_local_text_and_listing():
    at = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert local_text(at, "UTC") == "2026-01-15 12:00:00 UTC"
    request = PeriodRequest("UTC", 2026, 1)
    selection = Selection(request, datetime(2026, 1, 1, tzinfo=timezone.utc),
                          datetime(2026, 2, 1, tzinfo=timezone.utc), ["a"])
    text = render_selection(selection, [Txn("a", at)])
    assert text.startswith("Statement 2026-01 (UTC)") and "2026-01-15 12:00:00 UTC" in text
    assert text.endswith("1 transaction(s)\n")


def test_preview_range_and_cli_listing(tmp_path, capsys):
    txns = [Txn("a", datetime(2026, 1, 15, tzinfo=timezone.utc)), Txn("b", datetime(2026, 2, 15, tzinfo=timezone.utc))]
    assert [s.ids for s in preview_range(txns, "UTC", (2026, 1), (2026, 2))] == [["a"], ["b"]]
    (tmp_path / "txns.json").write_text(json.dumps([t.as_dict() for t in txns]), encoding="utf-8")
    (tmp_path / "request.json").write_text(json.dumps({"account_tz": "UTC", "year": 2026, "month": 1}), encoding="utf-8")
    main([str(tmp_path / "txns.json"), str(tmp_path / "request.json"), "--through", "2026-02"])
    output = capsys.readouterr().out
    assert "Statement 2026-01 (UTC)" in output and "Statement 2026-02 (UTC)" in output


def test_summary_table():
    from statements.render import render_summary, summary_rows
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    selections = [Selection(PeriodRequest("UTC", 2026, 1), start, start, ["a", "b"]),
                  Selection(PeriodRequest("UTC", 2026, 2), start, start, [])]
    assert summary_rows(selections) == [("2026-01", 2), ("2026-02", 0)]
    assert render_summary(selections).splitlines()[-1].split() == ["total", "2"]
