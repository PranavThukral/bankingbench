"""Synthetic named fee schedules used by demos and the offline preview tool."""
from fees.models import Schedule, Tier

CATALOG = {
    "starter": Schedule([Tier(None, 100, 10)], 25, 5000),
    "everyday": Schedule([Tier(10000, 150, 10), Tier(100000, 90, 20), Tier(None, 40, 50)], 25, 25000),
    "premium": Schedule([Tier(50000, 60, 0), Tier(None, 30, 25)], 0, 100000),
}


def schedule_names():
    return sorted(CATALOG)


def get_schedule(name):
    try:
        return CATALOG[name]
    except KeyError:
        raise KeyError(f"unknown schedule {name!r}; choose from {', '.join(schedule_names())}") from None
