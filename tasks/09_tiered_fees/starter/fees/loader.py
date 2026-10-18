"""Load fee schedules from versioned JSON files used by the offline preview tools."""
import json
from pathlib import Path
from fees.models import Schedule

SUPPORTED_VERSIONS = {1}


def load_schedule_file(path):
    """Read `{"version": 1, "schedule": {...}}` (or a bare schedule object) into a Schedule."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if "schedule" in document:
        if document.get("version") not in SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported schedule file version: {document.get('version')!r}")
        document = document["schedule"]
    return Schedule.from_dict(document)


def dump_schedule_file(path, schedule):
    document = {"version": 1, "schedule": schedule.as_dict()}
    Path(path).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
