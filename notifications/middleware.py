import json
import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("notifications.request")


class CorrelationIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        correlation_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )
        request.correlation_id = correlation_id.strip()
        request._start_time = time.time()

    def process_response(self, request, response):
        correlation_id = getattr(request, "correlation_id", None)
        if correlation_id:
            response["X-Correlation-ID"] = correlation_id
        try:
            duration_ms = int((time.time() - getattr(request, "_start_time", time.time())) * 1000)
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "method": request.method,
                        "path": request.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "correlation_id": correlation_id,
                    }
                )
            )
        except Exception:
            pass
        return response
