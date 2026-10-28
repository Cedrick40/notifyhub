# NotifyHub - Notification & Job Processing Service

NotifyHub accepts notification requests over a REST API, persists them durably, delivers them asynchronously via simulated providers (Email via Mailpit/SMTP, SMS/Push simulated), with retries, backoff, dead-lettering, and operator controls.

## Stack
- Python, Django, Django REST Framework
- PostgreSQL, Redis
- Celery
- Docker (for local dependencies)

## Quick Start (<= 5 commands)
From a fresh clone:

```bash
# 1) Start dependencies
docker compose up -d

# 2) Create and activate venv, install deps
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 3) Run migrations
python manage.py migrate

# 4) (Optional) Create API keys/clients via Django shell or admin
# 5) Run API and worker
python manage.py runserver &
celery -A config worker -l info &
```

Or with the venv python: `./venv/bin/python ...`

## Environment
Copy `.env.example` to `.env` and adjust as needed. Defaults are set for local docker-compose.

## API Endpoints
- `POST /v1/notifications` (requires header `X-API-Key` and `Idempotency-Key`) - submit a job, returns `202 Accepted`
- `GET /v1/notifications` - list jobs (producers see own; operators see all). Filters: `status`, `channel`, `created_after`, `created_before`. Paginated.
- `GET /v1/notifications/{id}` - get job with full attempt history
- `POST /v1/notifications/{id}/requeue` (operator only) - requeue a dead job
- `POST /v1/notifications/{id}/cancel` (operator only) - cancel a job
- `GET /v1/metrics` (operator only) - queue depth, outcome counts, retry counts, latency
- `GET /health` or `/v1/health` - health check
- `GET /docs/` - Swagger UI, `GET /schema/` - OpenAPI schema

## Authentication & Roles
Two roles: `producer` (submit and view own jobs) and `operator` (view all, requeue, cancel). Authenticate via header `X-API-Key`.

Create clients via Django shell:
```python
from notifications.models import Client
from notifications.auth import generate_api_key, hash_api_key
raw = generate_api_key()
Client.objects.create(name="other-service", api_key_hash=hash_api_key(raw), role=Client.Role.PRODUCER)
print(raw)
```

## Testing
```bash
python manage.py test
```

## Notes
- All providers are simulated. No real emails/SMS/push are sent.
- Idempotency enforced per client via `Idempotency-Key` header.
- Crash safety via leases; failed jobs retry with exponential backoff + jitter.
- Structured logs include correlation IDs; state changes create audit events.
