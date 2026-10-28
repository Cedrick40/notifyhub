# R6 - Dead jobs visible by status; operator can requeue them (audited)

**Implementation:** `POST /v1/notifications/<id>/requeue` in `notifications/views.py` (operator only via `IsOperator`). Validates job is DEAD, resets state to QUEUED (clears lease/next_attempt/last_error, resets attempt_count), enqueues after commit, logs audit event `requeued`.

**Evidence (tests):**
- `OperatorTests.test_producer_cannot_requeue` - producer gets 403
- `OperatorTests.test_operator_can_requeue_dead` - operator can requeue dead job → status becomes QUEUED
- Tests passing: see `evidence/R12_tests_setup.txt`
