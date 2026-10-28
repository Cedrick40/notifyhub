# R1 - POST /v1/notifications returns 202 Accepted with job id

**Implementation:** `notifications/views.py` - `NotificationListCreateView.post()` validates `Idempotency-Key` header, validates serializer, creates notification in transaction, enqueues after commit, returns `202 Accepted` with serialized data.

**Evidence (tests):**
- `AuthAndOwnershipTests.test_producer_can_submit_and_view_own` posts notification with valid auth + idempotency key and expects status 202; response contains id.
- Tests passing: see `evidence/R12_tests_setup.txt`

**Example request:**
```bash
curl -X POST http://localhost:8000/v1/notifications \
  -H "X-API-Key: <PROD_KEY>" \
  -H "Idempotency-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"channel":"email","recipient":"user@example.com","payload":{"subject":"Hi","body":"Test"}}'
```

**Expected response:** HTTP 202 with notification id, status queued, etc.
