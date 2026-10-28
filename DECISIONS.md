# Decisions

## ADR-001: API keys (SHA256 hashed) for auth
- **Context:** Need simple auth with two roles for this assignment.
- **Decision:** Use custom `X-API-Key` header, store `api_key_hash` (SHA256). Keys generated with `secrets.token_urlsafe`.
- **Trade-offs:** Simple and easy to test; no rotation/expiry. Acceptable for local/simulated scope.
- **Status:** Accepted

## ADR-002: PostgreSQL with SELECT FOR UPDATE SKIP LOCKED + leases
- **Context:** Need crash-safe consumption and at-least-once delivery.
- **Decision:** Claim jobs atomically with `select_for_update(skip_locked=True)`, set `locked_until` lease; expired leases are reclaimable.
- **Trade-offs:** Correct for at-least-once; requires idempotency/traceability (implemented). 
- **Status:** Accepted

## ADR-003: Exponential backoff with full jitter
- **Context:** Avoid retry storms on transient failures.
- **Decision:** `random.uniform(0, min(cap, base*2^attempt))` with cap.
- **Trade-offs:** Spreads retries; simpler than decorrelated jitter. Meets requirement.
- **Status:** Accepted

## ADR-004: SQLite for tests by default, Postgres optional
- **Context:** Postgres may not be available in all test environments.
- **Decision:** Default to SQLite for tests; set `USE_POSTGRES=true` to use Postgres (matches docker-compose).
- **Trade-offs:** Faster local tests; some PG-specific behaviors differ. Core logic is tested.
- **Status:** Accepted

## ADR-005: AuditLog model for state changes
- **Context:** Need traceability (R11).
- **Decision:** Separate `AuditLog` with correlation_id, metadata, client/notification.
- **Trade-offs:** Extra writes but explicit, queryable audit trail.
- **Status:** Accepted

## ADR-006: Enqueue after commit + swallow queue errors
- **Context:** API must return quickly and not fail if broker is down (R1/R3).
- **Decision:** Save in transaction, `transaction.on_commit(enqueue_notification)`, catch/enqueue errors and log.
- **Trade-offs:** Slight delay in enqueue but preserves durability; reconciler/worker can recover.
- **Status:** Accepted
