# Requirements Document: Notification & Job Processing Service

**Project:** Arrowstack Backend Development Internship, Project 2
**Author:** <Cederick Niyibikora>
**Version:** 1.0 (Week 1)
**Date:** <15/10/2026>
**Status:** Draft for mentor review

---

## 1. Purpose

Other systems in an organisation constantly need to tell people things: order confirmations, one-time passcodes, shipping updates. Sending these directly from the calling system is slow, fragile and leaves no record. This service accepts notification requests over a REST API, stores them durably, delivers them in the background through simulated providers, retries failures intelligently, and exposes the status and health of all work.

## 2. Stakeholder

**Organisation (fictional):** Cedmart, a mid-size online retailer.

**Primary stakeholder:** the Platform Engineering lead. Their order, payment and account services all need to send notifications, and today each service sends them inline. A slow or failing mail provider currently slows down checkout, and failed messages are lost with no trace.

**Secondary stakeholder:** the Operations/Support team, who field complaints such as "I never received my confirmation" and need to see exactly what happened to a message.

**Decisions this service enables:**

- Platform lead: when to add workers (queue depth and latency), and which provider is degrading (failure rates per channel).
- Support: whether a notification was delivered, retried or permanently failed, and requeueing it when appropriate.

**Measurable benefit:** callers get a response in well under a second regardless of provider health; no accepted notification is lost; every notification has a complete, queryable delivery history.

## 3. Scope

**In scope:** REST API for submitting and querying notifications; durable storage; background delivery; retries with backoff; dead-letter handling and operator requeue; authentication with two roles; structured logging and audit events; metrics; automated tests; one-command local setup.

**Out of scope:** a front-end UI; real email, SMS or push delivery (all providers are simulated); a template-authoring system; multi-tenant billing; Kubernetes or cloud deployment.

## 4. Functional Requirements

| ID | Requirement | Acceptance criterion | Evidence (fill in later) |
|---|---|---|---|
| R1 | `POST /v1/notifications` accepts a job (channel, recipient, payload, optional priority) and returns `202 Accepted` with a job id. | Valid request returns 202 and an id; invalid request returns a structured 4xx error. | |
| R2 | The same `Idempotency-Key` from the same client never creates two jobs. | Two identical requests, including concurrent ones, yield exactly one job and the same response. | |
| R3 | A job is persisted in the database before the client receives a response. | After a 202, killing the API process immediately still leaves the job in the database. | |
| R4 | A background worker consumes jobs and delivers them through a simulated provider. | A queued job reaches `succeeded` with a recorded attempt. | |
| R5 | Failed deliveries are retried with exponential backoff and jitter, up to a maximum number of attempts. Permanent errors are not retried. | Transient failures produce multiple attempts with growing delays; a permanent error produces exactly one attempt. | |
| R6 | Jobs that exhaust retries or fail permanently move to a `dead` state. An operator can requeue them. | Dead jobs are visible by status; requeue returns them to `queued` and is audited. | |
| R7 | `GET /v1/notifications/{id}` returns status and full attempt history. | Response lists every attempt with time, outcome and error. | |
| R8 | `GET /v1/notifications` supports filtering (status, channel, date) and pagination. | Filters narrow results correctly; pages are consistent. | |
| R9 | A metrics endpoint exposes queue depth, outcome counts, retry counts and delivery latency. | Metrics match counts in the database after a test run. | |
| R10 | Authentication with two roles: `producer` (submit and view own jobs) and `operator` (view all, requeue, cancel). | Missing or invalid credentials return 401; a producer attempting an operator action returns 403. | |
| R11 | All requests and state changes produce structured JSON logs with correlation ids; state-changing actions create audit events. | A job's lifecycle can be traced through logs and the audit table by id. | |
| R12 | Automated tests cover core logic, and the full stack starts with one command. | Test suite passes; a fresh clone runs in five commands or fewer. | |

## 5. Non-Functional Requirements

- **Reliability:** at-least-once delivery combined with idempotency, so no accepted job is lost and duplicate sends are prevented.
- **Crash safety:** a worker crash mid-job must not lose the job; it is recovered automatically after a lease timeout.
- **Security:** hashed API keys (or short-lived tokens), role checks on every route, input validation on every field, no secrets in version control, recipient details masked in logs.
- **Observability:** every job traceable from request to final outcome.
- **Reproducibility:** a mentor can run and review the work from the README alone.
- **Ethics and safety:** only simulated providers are used. No real messages are ever sent.

## 6. Success Metrics

These are proposed targets, set before building. They will be adjusted only with a written reason in `DECISIONS.md`.

| Metric | Target | How it will be measured |
|---|---|---|
| Job loss under worker crash | 0 lost out of 1,000 jobs when a worker is killed with `kill -9` mid-run | Chaos test script and final status counts |
| Duplicate sends | 0 duplicates per idempotency key | Integration test plus provider-side counter |
| Eventual delivery under failure | 99% or more succeed with 30% simulated transient failure and 5 attempts (theory: 0.3^5, about 0.24%, fail) | Simulation run compared against the calculation |
| Enqueue latency | p95 under 100 ms at 100 requests per second on a development laptop | Load test (k6 or Locust) |
| Test coverage | 80% or more on core logic (state machine, retry, idempotency, auth) | Coverage report |
| Reproducibility | Fresh clone to working stack in 5 commands or fewer | Clean-folder walkthrough |

## 7. Constraints and Assumptions

- Stack: Python, Django, Django REST Framework, PostgreSQL, Redis, Celery, Docker.
- Duration: four weeks, individual work, with mentor review at the end of weeks 1 and 3.
- Providers are simulated: Mailpit for email, and fake in-process providers for SMS and push with configurable failure modes.
- Assumption: callers can supply a unique idempotency key per logical notification.
- Assumption: development hardware is a single laptop, so performance targets are indicative, not production guarantees.

## 8. Overall Acceptance Criteria

The project is accepted when:

1. Requirements R1 to R12 are implemented and each is mapped to evidence in `evidence/`.
2. Every success metric in section 6 has been measured and recorded, whether it passed or failed.
3. A mentor can reproduce the work using only the README.
4. Known limitations and realistic next improvements are documented.
5. I can explain the key decisions, trade-offs and failure modes in the viva.

## 9. Glossary

- **Job / notification:** a durable record that a message must be attempted.
- **Idempotency key:** a client-supplied value that makes repeating a request safe.
- **Transient error:** a temporary failure worth retrying (timeout, 5xx).
- **Permanent error:** a failure retrying cannot fix (invalid recipient).
- **Dead state:** the terminal state for jobs that will not be retried automatically.
- **Lease:** a time-limited claim a worker holds on a job; if it expires, another worker may take over.