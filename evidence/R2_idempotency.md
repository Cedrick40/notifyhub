# R2 - Same Idempotency-Key from same client never creates two jobs

**Implementation:** Unique constraint on `(client, idempotency_key)`, `IntegrityError` caught on duplicate → return existing job with status 202 and header `Idempotent-Replayed: true`.

**Evidence (tests):**
- `IdempotencyTests.test_same_idempotency_key_same_response` verifies two identical requests yield same id and only 1 notification exists for the client.
- Tests passing: see `evidence/R12_tests_setup.txt`

**Behavior:** Concurrent/duplicate requests return the original job without creating duplicates.
