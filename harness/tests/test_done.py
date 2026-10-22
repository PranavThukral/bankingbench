import pytest
from harness.check_done import evaluate, repeat_ok


def test_check_done_all():
    metrics = {f"S{i}": True for i in range(1, 12)}
    metrics["docker_available"] = True
    assert all(status == "PASS" for _, status in evaluate(metrics))


@pytest.mark.parametrize("criterion", range(1, 12))
def test_check_done_each_missing(criterion):
    metrics = {f"S{i}": True for i in range(1, 12)}
    metrics.update(docker_available=True)
    metrics[f"S{criterion}"] = False
    rows = dict(evaluate(metrics))
    assert rows[f"S{criterion}"] == "FAIL"
    assert list(rows.values()).count("FAIL") == 1


def test_check_done_no_docker():
    assert dict(evaluate({}))["S4"] == "SKIP (no docker)"
    assert dict(evaluate({}))["S2"] == "FAIL"
    assert not repeat_ok({}, [], None, 3)


def test_s5_self_review_is_not_a_pass_and_not_a_failure():
    metrics = {f"S{i}": True for i in range(1, 12)}
    metrics.update(docker_available=True, S5="SELF-REVIEW")
    rows = dict(evaluate(metrics))
    assert rows["S5"] == "SELF-REVIEW"
    assert list(rows.values()).count("FAIL") == 0


def test_s5_requires_an_independent_receipt(tmp_path):
    from types import SimpleNamespace
    from harness.check_done import review_receipt, s5_status
    task = SimpleNamespace(id="toy_task", path=tmp_path)
    (tmp_path / "NOTES.md").write_text("## Blind review" + chr(10) + "No unresolved graded ambiguity" + chr(10))
    assert s5_status([task], tmp_path) == "SELF-REVIEW"          # NOTES text alone never passes
    (tmp_path / "reviews").mkdir()
    receipt = tmp_path / "reviews/toy_task.md"
    receipt.write_text("Author: Sam Park" + chr(10) + "Reviewer: Sam Park" + chr(10))
    assert not review_receipt(task, tmp_path) and s5_status([task], tmp_path) == "SELF-REVIEW"
    receipt.write_text("Author: Sam Park" + chr(10) + "Reviewer: Dana Lee" + chr(10))
    assert s5_status([task], tmp_path) is True
    (tmp_path / "NOTES.md").write_text("no claim")
    assert s5_status([task], tmp_path) is False


def test_s11_heldout_integrity(monkeypatch):
    from harness import check_done
    from harness.heldout import load_catalog
    from harness.discover import discover
    tasks = discover()
    assert not check_done.heldout_ok({}, tasks)                  # no receipt: fail
    rows = load_catalog(check_done.config.ROOT / "heldout/catalog.toml")
    runs = [dict(task=r["task"], variant=r["name"], expect=r["expect"], verdict="ok",
                 outcome="FAIL" if r["expect"] == "reject" else "PASS") for r in rows]
    monkeypatch.setattr(check_done, "matches", lambda receipt, t: True)
    import hashlib
    from harness.heldout import overlay_digests
    root = check_done.config.ROOT / "heldout"
    receipt = dict(runs=runs, catalog_digest=hashlib.sha256((root / "catalog.toml").read_bytes()).hexdigest(),
                   overlay_digests=overlay_digests(rows, root))
    assert check_done.heldout_ok(receipt, tasks)
    assert not check_done.heldout_ok({**receipt, "catalog_digest": "stale"}, tasks)
    assert not check_done.heldout_ok({**receipt, "runs": runs[:-1]}, tasks)
    bad = [dict(runs[0], outcome="PASS" if runs[0]["outcome"] == "FAIL" else "FAIL")] + runs[1:]
    assert not check_done.heldout_ok({**receipt, "runs": bad}, tasks)
    assert not check_done.heldout_ok({**receipt, "source_changed_during_run": True}, tasks)
