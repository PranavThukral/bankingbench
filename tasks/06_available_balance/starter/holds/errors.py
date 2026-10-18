"""Error responses shared by the HTTP adapter."""
from fastapi.responses import JSONResponse


def error(status, code, message=None):
    return JSONResponse({"error": {"code": code, "message": message or code}}, status_code=status)
