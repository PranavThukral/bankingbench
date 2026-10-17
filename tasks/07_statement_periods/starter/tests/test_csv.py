from datetime import datetime, timezone
import pytest
from statements.models import Txn, Selection, PeriodRequest
from statements.csv_io import read_csv, write_csv


def test_csv_round_trip(tmp_path):
    path = tmp_path / "records.csv"
    records = [Txn("a", datetime(2026, 1, 15, tzinfo=timezone.utc))]
    write_csv(path, records)
    assert read_csv(path) == records


@pytest.mark.parametrize("content", ["at,id\n2026-01-01,a\n", "id,at\na,2026-01-01\n",
                                    "id,at\na,2026-01-01T00:00:00Z\na,2026-01-02T00:00:00Z\n"])
def test_csv_rejects_invalid_records(tmp_path, content):
    path = tmp_path / "records.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        read_csv(path)


def test_selection_transport():
    request = PeriodRequest("UTC", 2026, 1)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 2, 1, tzinfo=timezone.utc)
    data = Selection(request, start, end, ["a"]).as_dict()
    assert data["ids"] == ["a"]
    assert data["request"] == request.as_dict()
    assert data["start"] == start.isoformat()
    assert data["end"] == end.isoformat()
