"""Request logging middleware for development debugging."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("cwlb.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration.

    For 4xx/5xx responses, also logs the response body so error details
    (e.g. FastAPI's "detail" field) appear in the terminal.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        status = response.status_code
        method = request.method
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"

        if status >= 400 and hasattr(response, "body_iterator"):
            # Read the body to include error detail in the log, then
            # reconstruct the response so the client still receives it.
            body_bytes = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    body_bytes += chunk.encode("utf-8")
                else:
                    body_bytes += chunk

            detail = body_bytes.decode("utf-8", errors="replace")
            # Trim to a reasonable length for log readability
            if len(detail) > 500:
                detail = detail[:500] + "..."

            log = logger.warning if status < 500 else logger.error
            log("%s %s → %d (%.0fms) — %s", method, path, status, duration_ms, detail)

            # Rebuild response with the consumed body
            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        logger.info("%s %s → %d (%.0fms)", method, path, status, duration_ms)
        return response
