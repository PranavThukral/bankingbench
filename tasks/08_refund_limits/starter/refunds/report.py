"""Summaries of processed refund requests for the support desk."""


def money(minor):
    major, cents = divmod(abs(minor), 100)
    return f"{'-' if minor < 0 else ''}{major}.{cents:02d}"


def summarize(results):
    """Counts and totals over the dictionaries produced by refunds.preview.process."""
    accepted = [r for r in results if r["accepted"]]
    rejected = {}
    for row in results:
        if not row["accepted"]:
            rejected[row["error"]] = rejected.get(row["error"], 0) + 1
    return {
        "requests": len(results),
        "accepted": len(accepted),
        "accepted_minor": sum(r["request"]["amount_minor"] for r in accepted),
        "rejected_by_error": dict(sorted(rejected.items())),
    }


def render_summary(results):
    data = summarize(results)
    lines = [f"requests: {data['requests']}", f"accepted: {data['accepted']} ({money(data['accepted_minor'])})"]
    lines += [f"rejected {name}: {count}" for name, count in data["rejected_by_error"].items()]
    return "\n".join(lines) + "\n"
