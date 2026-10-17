from pathlib import Path
import xml.etree.ElementTree as ET


def parse(path, returncode):
    counts = dict(total=0, passed=0, failed=0, errors=0, skipped=0)
    failures = []
    collection = returncode in {2, 4, 5}
    try:
        root = ET.parse(Path(path)).getroot()
        for case in root.iter("testcase"):
            counts["total"] += 1
            failure, error, skip = (case.find(x) for x in ("failure", "error", "skipped"))
            if error is not None:
                counts["errors"] += 1
                collection = True
            elif failure is not None:
                counts["failed"] += 1
            elif skip is not None:
                counts["skipped"] += 1
            else:
                counts["passed"] += 1
            if error is not None or failure is not None:
                failures.append(case.get("classname", "") + "::" + case.get("name", ""))
    except (ET.ParseError, OSError):
        collection = True
    if collection or not counts["total"] or returncode not in {0, 1}:
        outcome = "ERROR"
    elif counts["passed"] == counts["total"] and returncode == 0:
        outcome = "PASS"
    else:
        outcome = "FAIL"
    return outcome, counts, failures
