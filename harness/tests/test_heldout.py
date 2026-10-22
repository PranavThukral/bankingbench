import json
from pathlib import Path
import shutil

import pytest

from harness import config, heldout
from harness.discover import load_task


@pytest.mark.parametrize("inverted", [False, True])
def test_heldout_toy(tmp_path, monkeypatch, capsys, inverted):
    toy = Path(__file__).parent / "fixtures/toy_task"
    task_path = tmp_path / "tasks/toy_task"
    shutil.copytree(toy, task_path)
    shutil.copytree(config.ROOT / "graderlib", tmp_path / "graderlib")
    root = tmp_path / "heldout"
    catalog = []
    for name, variant, expect in [("good", "reference", "accept"),
                                  ("bad", "wrong_constant", "reject")]:
        shutil.copytree(toy / "solutions" / variant, root / "toy_task" / name)
        if inverted:
            expect = "reject" if expect == "accept" else "accept"
        catalog.append(f'[[probe]]\ntask="toy_task"\nname="{name}"\nexpect="{expect}"\n'
                       'description="Independent toy overlay."\n')
    (root / "catalog.toml").write_text("\n".join(catalog), encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(heldout, "discover", lambda **kw: [load_task(task_path)])
    assert heldout.main(["--jobs", "1", "--out", str(tmp_path / "results")]) == int(inverted)
    receipt = json.loads(next((tmp_path / "results").glob("*/heldout.json")).read_text())
    assert len(receipt["runs"]) == 2
    assert receipt["task_digests"]["toy_task"]
    assert len(receipt["overlay_digests"]) == 2
    assert not receipt["source_changed_during_run"]
    assert all(r["outcome"] in {"PASS", "FAIL"} for r in receipt["runs"])
    output = capsys.readouterr().out
    assert ("TOTAL | 0/1 | 0/1" if inverted else "TOTAL | 1/1 | 1/1") in output


def test_errors_do_not_count_as_catches():
    runs = [dict(task="toy_task", expect="reject", outcome="ERROR"),
            dict(task="toy_task", expect="accept", outcome="ERROR")]
    assert "TOTAL | 0/1 | 0/1" in heldout.table(runs)
