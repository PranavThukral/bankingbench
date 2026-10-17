import pytest
from harness.check_done import evaluate, repeat_ok


def test_check_done_all():
    metrics = {f"S{i}": True for i in range(1, 11)}
    metrics["docker_available"] = True
    assert all(status == "PASS" for _, status in evaluate(metrics))


@pytest.mark.parametrize("criterion", range(1, 11))
def test_check_done_each_missing(criterion):
    metrics = {f"S{i}": True for i in range(1, 11)}
    metrics.update(docker_available=True)
    metrics[f"S{criterion}"] = False
    rows = dict(evaluate(metrics))
    assert rows[f"S{criterion}"] == "FAIL"
    assert list(rows.values()).count("FAIL") == 1


def test_check_done_no_docker():
    assert dict(evaluate({}))["S4"] == "SKIP (no docker)"
    assert dict(evaluate({}))["S2"] == "FAIL"
    assert not repeat_ok({}, [], None, 3)
