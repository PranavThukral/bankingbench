import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "tasks"
RESULTS = ROOT / "results"
TMP = Path(os.environ.get("BB_TMP", str(Path(tempfile.gettempdir())  / "bankingbench")))
JOBS = min(4, os.cpu_count() or 1)
DETERMINISM = {
    "PYTHONHASHSEED": "0", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1",
    "HYPOTHESIS_PROFILE": "ci", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
}
