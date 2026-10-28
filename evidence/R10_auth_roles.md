# R10 - Authentication with two roles: producer and operator

**Implementation:** `ApiKeyAuthentication` via `X-API-Key`, `Client` model with roles. Producers submit/view own; operators view all and can do requeue/cancel. Permission checks enforced.

**Evidence (tests):**
- `AuthAndOwnershipTests.test_missing_auth_returns_401` - missing auth returns 401
- `AuthAndOwnershipTests.test_producer_cannot_see_others` - ownership enforced (404)
- `OperatorTests.test_producer_cannot_requeue` - producer attempting operator action gets 403
- `OperatorTests.test_operator_can_requeue_dead` - operator allowed
- Tests passing: see `evidence/R12_tests_setup.txt`
