"""
Audit logging middleware.

Logs every HTTP request with user_id (if authenticated), endpoint, method,
status code, and timestamp into a MongoDB 'audit_logs' collection.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import verify_access_token

logger = logging.getLogger("nutrimed.audit")


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests to the MongoDB audit_logs collection."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()

        # Extract user_id from JWT if present (best-effort, don't block request)
        user_id: Optional[str] = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
            try:
                payload = verify_access_token(token)
                user_id = payload.get("sub")
            except Exception:
                pass

        # Process the request
        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Build audit entry
        audit_entry = {
            "user_id": user_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else None,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.now(timezone.utc),
        }

        # Write to MongoDB asynchronously (fire-and-forget)
        try:
            from app.core.database import get_database

            db = get_database()
            # Motor insert_one returns a coroutine; we await it but don't let
            # failures break the response.
            await db["audit_logs"].insert_one(audit_entry)
        except Exception as exc:
            # Don't let audit failures affect the response
            logger.warning("Failed to write audit log: %s", exc)

        return response
