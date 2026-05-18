"""Cache-Control middleware for read-only API endpoints.

In production (debug=False), adds Cache-Control headers to GET responses
so browsers and CDNs can cache responses. In development (debug=True),
sets ``no-store`` so content is always fresh during iteration.

Cache strategy: 1-hour max-age + 24-hour stale-while-revalidate. When a
``DEPLOY_SHA`` env var is present, an ETag matching the deploy SHA is added
so browsers that revalidate after their max-age window get a fresh response
immediately after a new deploy instead of waiting up to an hour.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

# 1-hour max-age: browsers revalidate every hour at most. 24-hour
# stale-while-revalidate allows serving stale content while fetching fresh.
_PROD_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"
_DEV_CACHE_CONTROL = "no-store"

# ETag derived from the deploy SHA so clients invalidate on new deploys.
_ETAG: str | None = f'"sha-{settings.deploy_sha}"' if settings.deploy_sha else None


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control (and ETag) headers to GET responses on API routes.

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
                if _ETAG:
                    response.headers["ETag"] = _ETAG

        return response
