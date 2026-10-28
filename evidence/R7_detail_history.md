# R7 - GET /v1/notifications/{id} returns status and full attempt history

**Implementation:** `NotificationDetailView` with `NotificationDetailSerializer` includes `attempts` from `attempt_log` (prefetched). Ownership enforced.

**Evidence (tests):**
- `AuthAndOwnershipTests.test_producer_can_submit_and_view_own` retrieves detail successfully.
- Tests passing: see `evidence/R12_tests_setup.txt`
