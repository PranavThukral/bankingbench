import pytest
from fees.loader import load_schedule_file, dump_schedule_file
from fees.models import Schedule, Tier, FeePreview
from fees.report import effective_bps, summarize, render_summary, format_minor


def test_schedule_file_round_trip(tmp_path):
    schedule = Schedule([Tier(1000, 100, 1), Tier(None, 50, 2)], 0, 1000)
    dump_schedule_file(tmp_path / "schedule.json", schedule)
    assert load_schedule_file(tmp_path / "schedule.json") == schedule


def test_unsupported_version_is_rejected(tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text('{"version": 9, "schedule": {}}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_schedule_file(path)


def test_summary_uses_integer_arithmetic():
    rows = [FeePreview(10000, 150), FeePreview(0, 10), FeePreview(3, 1)]
    assert effective_bps(rows[0]) == 150 and effective_bps(rows[1]) == 0 and effective_bps(rows[2]) == 3333
    assert summarize(rows) == {"count": 3, "amount_total_minor": 10003, "fee_total_minor": 161,
                               "max_effective_bps": 3333}
    assert "fee total: 1.61" in render_summary(rows)
    assert format_minor(-5) == "-0.05"
    assert summarize([])["max_effective_bps"] == 0


def test_catalog_and_description():
    from fees.catalog import get_schedule, schedule_names
    from fees.report import describe_schedule
    assert schedule_names() == ["everyday", "premium", "starter"]
    text = describe_schedule(get_schedule("everyday"))
    assert "up to 100.00: 150 bps + 0.10" in text and text.endswith("fee limits: 0.25 to 250.00\n")
    with pytest.raises(KeyError):
        get_schedule("missing")
