import atexit
from pathlib import Path
import shutil
import tempfile


def pytest_configure(config):
    # Keep pytest's per-run directories in the system temp dir, never inside the repository.
    # (A shared user-wide pytest directory can have incompatible ACLs on Windows.)
    parent = Path(tempfile.mkdtemp(prefix="bankingbench-pytest-"))
    atexit.register(shutil.rmtree, parent, ignore_errors=True)
    config.option.basetemp = str(parent / "run")
