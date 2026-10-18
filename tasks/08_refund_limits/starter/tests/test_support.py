import pytest
from refunds.csvio import read_requests_csv, write_results_csv
from refunds.preview import process
from refunds.report import money, render_summary, summarize
from refunds.models import RefundRequest
from refunds.service import RefundService


def test_money_and_summary_of_processed_rows():
    rows = [
        {"accepted": True, "refund_id": 1, "request": {"payment_id": 1, "amount_minor": 250}},
        {"accepted": False, "error": "RefundExceedsCaptured", "request": {"payment_id": 1, "amount_minor": 9000}},
        {"accepted": False, "error": "RefundExceedsCaptured", "request": {"payment_id": 1, "amount_minor": 9001}},
    ]
    assert money(250) == "2.50" and money(-5) == "-0.05"
    assert summarize(rows) == {"requests": 3, "accepted": 1, "accepted_minor": 250,
                               "rejected_by_error": {"RefundExceedsCaptured": 2}}
    assert "rejected RefundExceedsCaptured: 2" in render_summary(rows)


def test_csv_requests_round_trip_through_a_service(tmp_path):
    (tmp_path / "requests.csv").write_text("payment_id,amount_minor\n1,40\n1,10\n", encoding="utf-8")
    service = RefundService(tmp_path / "db")
    payment = service.create_payment(100)
    service.capture(payment, 100)
    requests = read_requests_csv(tmp_path / "requests.csv")
    assert requests == [RefundRequest(1, 40), RefundRequest(1, 10)]
    results = process(service, requests)
    assert [r["accepted"] for r in results] == [True, True]
    write_results_csv(tmp_path / "results.csv", results)
    text = (tmp_path / "results.csv").read_text(encoding="utf-8")
    assert text.splitlines()[0] == "payment_id,amount_minor,accepted,refund_id,error"
    assert text.splitlines()[1].startswith("1,40,True,")


def test_csv_requests_report_the_bad_line(tmp_path):
    (tmp_path / "requests.csv").write_text("payment_id,amount_minor\n1,40\n1,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 3"):
        read_requests_csv(tmp_path / "requests.csv")
