"""Cache-Control middleware for read-only API endpoints.

In production (debug=False), adds Cache-Control headers to GET responses
so browsers and CDNs can cache responses. In development (debug=True),
sets ``no-store`` so content is always fresh during iteration.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

# Cache for 5 min, allow stale-while-revalidate for 1 hour.
_PROD_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=3600"
_DEV_CACHE_CONTROL = "no-store"


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control headers to GET responses on API routes.

    Skips non-GET methods, non-API paths, and error responses.
    In debug mode, sends ``no-store`` to prevent stale data during
    development.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Only cache successful GET requests on API routes
        if (
            request.method == "GET"
            and request.url.path.startswith("/api/")
            and 200 <= response.status_code < 300
        ):
            if settings.debug:
                response.headers["Cache-Control"] = _DEV_CACHE_CONTROL
            else:
                response.headers["Cache-Control"] = _PROD_CACHE_CONTROL

        return response
