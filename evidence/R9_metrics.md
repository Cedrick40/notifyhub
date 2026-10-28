# R9 - Metrics endpoint exposes queue depth, outcome counts, retry counts, delivery latency

**Implementation:** `GET /v1/metrics` (operator only) returns queue_depth, processing, dead, succeeded, by_status, outcome_counts, retry_counts, delivery_latency (avg seconds), timestamp.

**Evidence:** Implemented in `notifications/views.py`, routed in `notifications/urls.py` and also available under `/v1/metrics`.
