# R3 - Job persisted before client receives response

**Implementation:** Notification saved inside `transaction.atomic()` block before returning response; `enqueue_notification` called via `transaction.on_commit()`. Job is committed to DB before 202 response.

**Evidence:** Code structure in `notifications/views.py` ensures persistence prior to response. Transactional behavior verified by implementation pattern.
