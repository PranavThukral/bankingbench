import json
from fees.models import Schedule, Tier
from fees.preview import read_amounts, read_schedule, preview, write_preview


def test_read_schedule(tmp_path):
    schedule = Schedule([Tier(None, 100, 5)], 0, 1000)
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps(schedule.as_dict()), encoding="utf-8")
    assert read_schedule(path) == schedule


def test_read_amounts(tmp_path):
    path = tmp_path / "amounts.csv"
    path.write_text("amount_minor\n100\n200\n", encoding="utf-8")
    assert read_amounts(path) == [100, 200]


def test_preview_and_csv(tmp_path):
    schedule = Schedule([Tier(None, 100, 5)], 0, 1000)
    rows = preview([1000], schedule)
    assert rows[0].fee_minor == 15
    assert rows[0].total_minor == 1015
    path = tmp_path / "preview.csv"
    write_preview(path, rows)
    assert "1000,15,1015" in path.read_text(encoding="utf-8")
