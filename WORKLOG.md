# Worklog

## 2026-10-27
- Scaffolded Django project, docker-compose (Postgres/Redis/Mailpit), core models/migrations (commit 0b1ca27)
- Added OpenAPI schema + Swagger UI (commit 711b5cd)
- Added list/detail endpoints with ownership rules (commit 056e93d)
- Added AuditLog model, correlation-id middleware, structured JSON logging
- Added operator actions (requeue/cancel), metrics endpoint, health endpoints
- Added date/status/channel filtering, role-based permissions, audit events
- Added tests, README.md
- Tests passing: `python manage.py test` (8 tests OK)

## 2026-10-28
- Fixed list queryset duplication, improved date filtering (created_after/before/date/from/to)
- Enhanced permissions/messages and allowed hosts for local testing
- Verified system checks and tests passing
- Preparing evidence for R1-R12
