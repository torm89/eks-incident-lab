"""Error responses in the Anthropic API format, so SDK clients react as they would to the real API."""

from fastapi.responses import JSONResponse

ERROR_TYPES = {
    400: "invalid_request_error",
    401: "authentication_error",
    403: "permission_error",
    404: "not_found_error",
    413: "request_too_large",
    429: "rate_limit_error",
    529: "overloaded_error",
}
DEFAULT_ERROR_TYPE = "api_error"
RATE_LIMIT_RETRY_AFTER_SECONDS = "2"


def error_response(status_code: int, message: str) -> JSONResponse:
    error_type = ERROR_TYPES.get(status_code, DEFAULT_ERROR_TYPE)
    headers = {"retry-after": RATE_LIMIT_RETRY_AFTER_SECONDS} if status_code == 429 else None
    return JSONResponse(
        status_code=status_code,
        content={"type": "error", "error": {"type": error_type, "message": message}},
        headers=headers,
    )
