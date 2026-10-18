"""Pattern-based SBF-80 record decoding (regular expressions instead of column slicing)."""
from datetime import datetime
import re
from batch.models import Payment

CURRENCY = "CAD|USD|EUR|GBP|JPY|KWD|BHD"
HEADER = re.compile(rf"H[A-Z0-9]{{12}}([0-9]{{8}})(?:{CURRENCY}) {{56}}")
DETAIL = re.compile(r"D([0-9]{12})([0-9]{12})([ -~]{20}) {35}")
TRAILER = re.compile(r"T([0-9]{6})([0-9]{15})([0-9]{10}) {48}")
PRINTABLE = re.compile(rb"[\x20-\x7e]*")
LINE_END = re.compile(rb"\r?\n")


def physical_lines(data):
    """Split on LF or CRLF terminators; an unterminated final line is kept as it is."""
    if not data:
        return []
    pieces = LINE_END.split(data)
    if pieces[-1] == b"":
        pieces.pop()
    return pieces


def decode(raw):
    if not PRINTABLE.fullmatch(raw):
        return None, "invalid_encoding"
    if len(raw) != 80:
        return None, "line_length"
    return raw.decode("ascii"), None


def header_ok(match):
    try:
        datetime.strptime(match.group(1), "%Y%m%d")
    except ValueError:
        return False
    return True


def fields(text):
    kind = text[0]
    if kind == "H":
        match = HEADER.fullmatch(text)
        return None, None if match and header_ok(match) else "invalid_header"
    if kind == "D":
        match = DETAIL.fullmatch(text)
        if not match or int(match.group(2)) <= 0 or not match.group(3).strip():
            return None, "invalid_detail"
        return Payment(match.group(1), int(match.group(2)), match.group(3).rstrip(" ")), None
    if kind == "T":
        match = TRAILER.fullmatch(text)
        if not match:
            return None, "invalid_trailer"
        return tuple(int(group) for group in match.groups()), None
    return None, "record_type"
