import uuid

from .models import AuditLog


def get_correlation_id(request=None):
    if request is not None:
        cid = getattr(request, "correlation_id", None)
        if cid:
            return cid
        # try header
        for header in ("X-Correlation-ID", "X-Request-ID", "Correlation-ID"):
            cid = request.headers.get(header)
            if cid:
                return cid.strip()
    return str(uuid.uuid4())


def log_audit(action, notification=None, client=None, request=None, metadata=None, correlation_id=None):
    if correlation_id is None:
        correlation_id = get_correlation_id(request)
    ip_address = None
    if request is not None:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")
    try:
        AuditLog.objects.create(
            notification=notification,
            client=client,
            action=action,
            correlation_id=correlation_id or "",
            metadata=metadata or {},
            ip_address=ip_address,
        )
    except Exception:
        # Never let audit logging break the request path
        pass
