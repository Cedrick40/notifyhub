# R8 - GET /v1/notifications supports filtering (status, channel, date) and pagination

**Implementation:** `NotificationListCreateView.get_queryset()` filters by status/channel with validation; adds date filtering via `created_after`/`created_before`/`date`/`from`/`to`. DRF PageNumberPagination configured (PAGE_SIZE 20).

**Evidence:** Implemented in `notifications/views.py`. Schema updated with filter params.
