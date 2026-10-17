from pathlib import Path
import tomllib
import pytest

from harness.discover import load_task
from harness.export_harbor import export_task, validate_task, validate_config

TOY = Path(__file__).parent / "fixtures/toy_task"


def test_export_harbor_toy(tmp_path):
    task = load_task(TOY)
    output = export_task(task, tmp_path)
    for name in ["instruction.md", "task.toml", "environment/Dockerfile", "tests/test.sh", "solution/solve.sh"]:
        assert (output / name).is_file()
    meta = tomllib.loads((output / "task.toml").read_text())
    assert meta["task"]["name"] == "synthetic/toy_task"
    result = validate_task(task, output)
    assert result["reference_reward"] == 1 and result["starter_reward"] == 0


def test_export_rejects_undocumented_keys(tmp_path):
    output = export_task(load_task(TOY), tmp_path)
    path = output / "task.toml"
    path.write_text(path.read_text() + '\ncompose_path = "guessed.yml"\n')
    with pytest.raises(ValueError, match="undocumented"):
        validate_config(path)
