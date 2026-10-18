"""Fixed-width record decoding shared by offline batch utilities."""
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
    """Decode the columns of one 80-character record. Only detail records are interpreted so far."""
    if text[0] == "D":
        valid = digits(text[1:13]) and digits(text[13:25]) and text[45:] == " " * 35
        if not valid or int(text[13:25]) <= 0 or not text[25:45].strip():
            return None, "invalid_detail"
        return Payment(text[1:13], int(text[13:25]), text[25:45].rstrip(" ")), None
    return None, None


def physical_lines(data):
    if not data:
        return []
    rows = data.split(b"\n")
    if rows[-1] == b"":
        rows.pop()
    return rows
