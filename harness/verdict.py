def hits(must_fail, failed_tests):
    return [test for test in must_fail if any(
        node.rsplit("::", 1)[-1].split("[", 1)[0] == test for node in failed_tests)]


def decide(expected, outcome, must_fail=(), failed_tests=()):
    if outcome == "ERROR":
        return "infra_error"
    if expected == "PASS":
        return "ok" if outcome == "PASS" else "false_fail"
    if outcome == "PASS":
        return "false_pass"
    return "ok" if not must_fail or hits(must_fail, failed_tests) else "ok_wrong_reason"
