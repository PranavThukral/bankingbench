import re
from collections import Counter
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


SUMMARY = re.compile(r"(\d+) (passed|failed|errors?|skipped)")


def case_ids(path):
    """Return the (classname, name) of every testcase in a JUnit file, in file order."""
    root = ET.parse(Path(path)).getroot()
    return [(c.get("classname", ""), c.get("name", "")) for c in root.iter("testcase")]


def base_name(name):
    return name.split("[", 1)[0]


def parse_checked(path, returncode, manifest=None, stdout=""):
    """Like parse(), but distrusts the file: cross-check the manifest, exit code and summary line.

    Returns (outcome, counts, failures, reason). Any inconsistency yields ERROR with a reason.
    manifest is {"mode": "collected"|"ast", "ids": [[classname, name], ...]}.
    """
    outcome, counts, failures = parse(path, returncode)
    if outcome == "ERROR":
        return outcome, counts, failures, "pytest error, collection error or unreadable JUnit file"
    try:
        found = case_ids(path)
    except (ET.ParseError, OSError):
        return "ERROR", counts, failures, "unreadable JUnit file"
    if manifest is not None:
        expected = [tuple(i) for i in manifest["ids"]]
        if manifest["mode"] == "collected":
            want, have = Counter(expected), Counter(found)
        else:  # AST fallback knows only function names, not parametrize ids
            want = Counter((c, n) for c, n in expected)
            have = Counter((c, base_name(n)) for c, n in found)
            want, have = set(want), set(have)
        missing, extra = _diff(want, have)
        if missing or extra:
            reason = "JUnit results do not match the expected-test manifest"
            if missing:
                reason += f"; missing: {sorted(missing)[:5]}"
            if extra:
                reason += f"; unexpected: {sorted(extra)[:5]}"
            return "ERROR", counts, failures, reason
    if counts["failed"] + counts["errors"] and returncode == 0:
        return "ERROR", counts, failures, f"pytest exit code {returncode} contradicts the JUnit counts"
    if returncode == 1 and not (counts["failed"] + counts["errors"]):
        return "ERROR", counts, failures, "pytest exit code 1 but JUnit records no failure"
    summary = {}
    last = [line for line in stdout.splitlines() if SUMMARY.search(line)]
    if not last:
        return "ERROR", counts, failures, "no pytest summary line in the output"
    for number, label in SUMMARY.findall(last[-1]):
        key = "errors" if label.startswith("error") else label
        summary[key] = int(number)
    for key in ("passed", "failed", "errors", "skipped"):
        if summary.get(key, 0) != counts[key]:
            return ("ERROR", counts, failures,
                    f"pytest summary reports {summary} but JUnit counts are {counts}")
    return outcome, counts, failures, ""


def _diff(want, have):
    if isinstance(want, Counter):
        return list((want - have).elements()), list((have - want).elements())
    return list(want - have), list(have - want)
