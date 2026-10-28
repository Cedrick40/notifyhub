# R4 - Background worker delivers via simulated provider, reaches succeeded with attempt

**Implementation:** `notifications/tasks.py` - `claim_notification()` atomically claims job (with lease), creates `NotificationAttempt`; `send_notification()` calls `deliver()`; on success calls `_finish()` with `SUCCESS` and `SUCCEEDED`. `notifications/providers.py` implements simulated delivery.

**Evidence:** Worker logic in place with attempt recording. Provider simulation + SMTP for email configured.
