from batch.models import BatchResult, Payment, BatchError  # noqa: F401
from batch.records import fields, decode, physical_lines


def parse(data):
    physical = physical_lines(data)
    issues = set()
    details = []
    number_of_details, amount_sum, account_sum = 0, 0, 0
    controls = []
    last_index = len(physical)
    if not physical or not physical[0].startswith(b"H"):
        issues.add((1, "missing_header"))
    if not physical or not physical[-1].startswith(b"T"):
        issues.add((max(last_index, 1), "missing_trailer"))
    for index, physical_record in enumerate(physical, start=1):
        marker = physical_record[:1]
        if marker == b"D":
            number_of_details += 1
        expected_position = {b"H": index == 1, b"T": index == last_index,
                             b"D": 1 < index < last_index}
        if marker in expected_position and not expected_position[marker]:
            issues.add((index, "record_order"))
        record, issue = decode(physical_record)
        if issue is None:
            value, issue = fields(record)
            if issue is None and marker == b"D":
                details.append(value)
                amount_sum += value.amount_minor
                account_sum = (account_sum + int(value.payee_account[-8:])) % 10**10
            elif issue is None and marker == b"T":
                controls.append((index, value))
        if issue:
            issues.add((index, issue))
    for index, declared in controls:
        observed = number_of_details, amount_sum, account_sum
        codes = "count_mismatch", "control_total_mismatch", "hash_total_mismatch"
        for i, code in enumerate(codes):
            if declared[i] != observed[i] or (i == 0 and number_of_details == 0):
                issues.add((index, code))
    ordered_errors = [BatchError(line, code) for line, code in sorted(issues)]
    if ordered_errors:
        return BatchResult(False, [], ordered_errors)
    return BatchResult(True, details, [])
