# Evidence Index

Every file in this folder must be **real output from my own runs**, with the date captured. This index maps each requirement to the evidence that proves it. A requirement with an empty evidence cell is not finished.

## How to capture the baseline evidence (run from the project root, venv active, containers up)

```bash
mkdir -p evidence/screenshots

# Environment and versions
{ date; python --version; docker --version; docker compose version; pip freeze; } > evidence/environment.txt

# Running infrastructure
docker compose ps > evidence/containers.txt

# Database tables
docker compose exec postgres psql -U notifyhub -d notifyhub -P pager=off -c "\dt" > evidence/tables.txt

# API contract generated from the code
python manage.py spectacular --file evidence/openapi-schema.yml

# Commit history with dates
git log --date=short --pretty=format:"%ad %h %s" > evidence/git-history.txt

# Job outcomes right now (re-run after each experiment, with a new file name)
docker compose exec postgres psql -U notifyhub -d notifyhub -P pager=off \
  -c "select status, count(*) from notifications_notification group by status order by 2 desc;" \
  > evidence/status-counts-$(date +%F).txt
```

## Evidence from Swagger UI

In Swagger, the response panel has a **Download** button for response bodies. Save these into this folder, and take screenshots (including the status code and headers) into `screenshots/`:

| File | What to capture |
|---|---|
| `screenshots/post-202.png` | Successful submission: 202, job id, status `queued` |
| 
| `screenshots/post-400-validation.png` | A rejected request with a clear validation error |
| `screenshots/post-401.png` | A request with no or invalid API key |
| `screenshots/get-404-other-client.png` | Another producer asking for my job: 404 |
| `screenshots/get-operator-200.png` | Operator asking for the same job: 200 |
| `screenshots/requeue-403-producer.png` | Producer attempting requeue: 403 |
| `dead-job-detail.json` | A job that exhausted retries, showing all attempts |
| `audit-trail-example.json` | The audit trail of one job (created, retrying or dead, requeued, succeeded) |

## Requirement-to-evidence map

| Req | Requirement (short) | Evidence file(s) | Status |
|---|---|---|---|
| R1 | POST returns 202 with job id | `screenshots/post-202.png`, `openapi-schema.yml` | |
| R2 | Idempotency key prevents duplicates | `screenshots/post-replay.png`, database query showing one row per key | |
| R3 | Job persisted before the response | Test output (planned): kill the API after 202 and show the row | |
| R4 | Worker delivers via simulated provider | `status-counts-*.txt`, Mailpit screenshot | |
| R5 | Retries with backoff and jitter; permanent errors not retried | `dead-job-detail.json` (five attempts) and a one-attempt permanent failure detail | |
| R6 | Dead state and operator requeue | `screenshots/requeue-403-producer.png`, `audit-trail-example.json` | |
| R7 | Status plus attempt history endpoint | `dead-job-detail.json` | |
| R8 | List with filters and pagination | Screenshot of list and filtered list | |
| R9 | Metrics endpoint | Not built yet | |
| R10 | Authentication and roles | `post-401.png`, `get-404-other-client.png`, `get-operator-200.png`, `requeue-403-producer.png` | |
| R11 | Structured logs and audit events | `audit-trail-example.json`; log samples (planned) | |
| R12 | Automated tests and one-command setup | Test and coverage reports (planned) | |

## Success-metric evidence (from `docs/requirements.md`, section 6)

| Metric | Evidence file | Result | Pass? |
|---|---|---|---|
| Job loss under worker crash | `chaos-kill-worker.txt` (planned) | | |
| Duplicate sends | integration test output (planned) | | |
| Eventual delivery under 30% transient failure | `status-counts-*.txt` of a batch run | | |
| Enqueue latency p95 | `loadtest-results.txt` (planned) | | |
| Test coverage | `coverage-report.txt` (planned) | | |
| Reproducibility from a fresh clone | `fresh-clone-walkthrough.md` (planned) | | |

## Rules for this folder
1. Never edit or fake evidence. If a run fails a metric, record the failure and what I did about it.
2. Name files with the date when an experiment can be repeated (`status-counts-YYYY-MM-DD.txt`).
3. Remove any real credentials or API keys from screenshots and files before committing.