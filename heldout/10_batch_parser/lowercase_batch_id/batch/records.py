"""Fixed-width record decoding shared by offline batch utilities."""
from datetime import datetime
import re
from batch.models import Payment

CURRENCIES = {"CAD", "USD", "EUR", "GBP", "JPY", "KWD", "BHD"}


def digits(text):
    return bool(text) and all("0" <= char <= "9" for char in text)


def decode(raw):
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return None, "invalid_encoding"
    if any(ord(c) < 32 or ord(c) > 126 for c in text):
        return None, "invalid_encoding"
    if len(text) != 80:
        return None, "line_length"
    return text, None


def fields(text):
    kind = text[0]
    if kind == "H":
        valid = bool(re.fullmatch(r"[A-Za-z0-9]{12}", text[1:13]))
        try:
            datetime.strptime(text[13:21], "%Y%m%d")
            valid = valid and digits(text[13:21])
        except ValueError:
            valid = False
        valid = valid and text[21:24] in CURRENCIES and text[24:] == " " * 56
        return None, None if valid else "invalid_header"
    if kind == "D":
        valid = digits(text[1:13]) and digits(text[13:25]) and text[45:] == " " * 35
        if not valid or int(text[13:25]) <= 0 or not text[25:45].strip():
            return None, "invalid_detail"
        return Payment(text[1:13], int(text[13:25]), text[25:45].rstrip(" ")), None
    if kind == "T":
        if not (digits(text[1:7]) and digits(text[7:22]) and digits(text[22:32]) and text[32:] == " " * 48):
            return None, "invalid_trailer"
        return (int(text[1:7]), int(text[7:22]), int(text[22:32])), None
    return None, "record_type"


def physical_lines(data):
    if not data:
        return []
    rows = data.split(b"\n")
    if rows[-1] == b"":
        rows.pop()
    return [row[:-1] if row.endswith(b"\r") and (i < len(rows) - 1 or data.endswith(b"\n")) else row
            for i, row in enumerate(rows)]
