# R11 - Structured JSON logs with correlation ids; audit events for state changes

**Implementation:** `CorrelationIdMiddleware` adds/generates correlation IDs and logs structured JSON requests; JSON formatter in `notifications/logging_utils.py`; logging configured. `AuditLog` model + `notifications/audit.py` logs events (submitted, enqueued, started, retried, succeeded, dead, requeued, cancelled).

**Evidence:** Middleware integrated in settings, audit logging added to views and tasks. Tests show structured logs in output.
