# R5 - Retries with exponential backoff + jitter, up to max attempts; permanent errors not retried

**Implementation:** `backoff_seconds()` uses exponential with full jitter, capped by settings. `send_notification()` catches `TransientError` - if attempts exhausted → DEAD; else sets RETRYING, records attempt outcome `TRANSIENT_FAILURE`, calls `self.retry(countdown=delay)`. `PermanentError` goes to DEAD with no retry.

**Evidence:** Code in `notifications/tasks.py`. Max attempts default 5 from model.
