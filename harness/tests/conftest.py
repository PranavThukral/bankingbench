from pathlib import Path
import uuid


def pytest_configure(config):
    # Avoid a shared user-wide pytest directory with incompatible ACLs on Windows.
    parent = Path(__file__).resolve().parents[2] / ".test-tmp"
    parent.mkdir(exist_ok=True)
    config.option.basetemp = str(parent / uuid.uuid4().hex)
