"""Operator-facing descriptions for batch error codes."""

DESCRIPTIONS = {
    "invalid_encoding": "record contains non-ASCII or control characters",
    "line_length": "record is not exactly 80 characters",
    "record_type": "record type is not H, D or T",
    "record_order": "record is in the wrong position in the file",
    "invalid_header": "header fields are malformed",
    "invalid_detail": "detail fields are malformed",
    "invalid_trailer": "trailer fields are malformed",
    "count_mismatch": "trailer detail count does not match the file",
    "control_total_mismatch": "trailer control total does not match the details",
    "hash_total_mismatch": "trailer hash total does not match the payee accounts",
    "missing_header": "file does not start with a header record",
    "missing_trailer": "file does not end with a trailer record",
}


def describe(code):
    return DESCRIPTIONS.get(code, "unrecognised error code")


def render_errors(errors):
    """One line per error: `line 7: invalid_detail - detail fields are malformed`."""
    return "".join(f"line {error.line_no}: {error.code} - {describe(error.code)}\n" for error in errors)
