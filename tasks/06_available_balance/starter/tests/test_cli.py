from holds.cli import overview
from holds.storage import transaction
from holds.summary import money, render_overview


def test_overview_lists_seeded_accounts(tmp_path):
    rows = overview(tmp_path / "db")
    assert [(r["id"], r["posted"], r["overdraft"]) for r in rows] == [
        ("acct_flex", 10000, 5000), ("acct_standard", 10000, 0)]
    assert all(r["authorizations"] == {} for r in rows)


def test_overview_counts_authorization_records_by_state(tmp_path):
    overview(tmp_path / "db")
    with transaction(tmp_path / "db") as db:
        db.executemany("INSERT INTO authorizations VALUES (?,?,?,?,?)", [
            ("a", "acct_standard", 100, 0.0, "active"), ("b", "acct_standard", 50, 0.0, "active"),
            ("c", "acct_standard", 10, 0.0, "voided")])
    rows = {r["id"]: r for r in overview(tmp_path / "db")}
    assert rows["acct_standard"]["authorizations"] == {"active": 2, "voided": 1}


def test_render_overview_formats_money():
    assert money(-250) == "-2.50" and money(5) == "0.05"
    text = render_overview([dict(id="acct_x", posted=12345, overdraft=0, authorizations={})])
    assert "acct_x" in text and "123.45" in text and "none" in text


def test_export_authorizations_csv(tmp_path):
    from holds.export import export_authorizations
    overview(tmp_path / "db")
    with transaction(tmp_path / "db") as db:
        db.execute("INSERT INTO authorizations VALUES ('a','acct_standard',100,0.0,'active')")
    assert export_authorizations(tmp_path / "db", tmp_path / "out.csv") == 1
    text = (tmp_path / "out.csv").read_text(encoding="utf-8")
    assert text.splitlines()[0] == "auth_id,account,amount_minor,created_at,state"
    assert "a,acct_standard,100,1970-01-01T00:00:00+00:00,active" in text


def test_manual_clock_advances_only_on_request():
    from datetime import datetime, timedelta, timezone
    from holds.clock import ManualClock, instant
    clock = ManualClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    first = instant(clock)
    assert instant(clock) == first
    clock.advance(timedelta(hours=1))
    assert instant(clock) == first + 3600
