"""Request body validation for the account endpoints."""


async def amount(request):
    """Return the positive integer `amount_minor` of a request body, or None if the body is invalid."""
    try:
        body = await request.json()
    except ValueError:
        return None
    if not isinstance(body, dict) or set(body) != {"amount_minor"}:
        return None
    value = body["amount_minor"]
    return value if type(value) is int and value > 0 else None
