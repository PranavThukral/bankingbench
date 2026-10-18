"""Quote many requests at once; a bad request is reported, not fatal."""
import csv
from pathlib import Path
from fx.models import RateUnavailable
from fx.quote import quote_transfer

COLUMNS = ["amount_minor", "src", "dst", "fee_bps", "status", "fee_minor", "converted_minor", "path"]


def quote_all(requests, rates, quote=quote_transfer):
    """Return [(status, quote_or_None)] in request order; status is ok, no_route or invalid."""
    outcomes = []
    for request in requests:
        try:
            outcomes.append(("ok", quote(request.amount_minor, request.src, request.dst, rates, request.fee_bps)))
        except RateUnavailable:
            outcomes.append(("no_route", None))
        except ValueError:
            outcomes.append(("invalid", None))
    return outcomes


def write_quotes_csv(path, requests, outcomes):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        for request, (status, result) in zip(requests, outcomes):
            fields = [request.amount_minor, request.src, request.dst, request.fee_bps, status]
            fields += [result.fee_minor, result.converted_minor, ">".join(result.path)] if result else ["", "", ""]
            writer.writerow(fields)
    return len(requests)
