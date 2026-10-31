Phase 1: Producer A
Open http://localhost:8000/docs/.
post-401.png: click Authorize, then Logout if a key is stored, then close. Padlock open. Run POST /v1/notifications with Idempotency-Key: ev-401 and the standard body. Expect 401. Screenshot.
Authorize with key A.
post-202.png: Idempotency-Key: ev-001, standard body, Execute. Expect 202, an id, "status": "queued". Screenshot.
post-replay.png: press Execute again with the same key. Expect the same id and the header idempotent-replayed: true. Make sure the header is in the crop. Screenshot.
post-400-validation.png: change the key to ev-400 and set "recipient": "not-an-email". Expect 400 naming the recipient. Screenshot.
Phase 2: Create the dead job
Tab 3: edit .env so these two lines read:
FAKE_TRANSIENT_RATE=1.0
FAKE_PERMANENT_RATE=0.0
Tab 2: press Ctrl+C, then Up arrow, then Enter, to restart the worker. This step is essential, because the worker only reads .env at startup.
As A, run POST /v1/notifications with Idempotency-Key: ev-dead and a valid standard body. Copy the id into a note.
Wait about 40 seconds, watching tab 2 retry. Then run GET /v1/notifications/{id} with that id. Expect "status": "dead" and five entries under attempts. If it says retrying, wait ten seconds and execute again.
dead-job-detail.json: click Download on the response body. Move the file into notifyhub/evidence/ and rename it dead-job-detail.json.
Phase 3: Ownership and roles (use the dead job’s id)
get-404-other-client.png: Logout, then Authorize with key B. Run GET /v1/notifications/{id}. Expect 404. Screenshot.
requeue-403-producer.png: still as B, run POST /v1/notifications/{id}/requeue. Expect 403, “Operator role required.” Screenshot.
get-operator-200.png: Logout, then Authorize with key Op. Run GET /v1/notifications/{id}. Expect 200 with the full record. Screenshot.
Phase 4: Requeue and audit trail
Tab 3: edit .env so both rates are zero:
FAKE_TRANSIENT_RATE=0.0
FAKE_PERMANENT_RATE=0.0
Tab 2: restart the worker (Ctrl+C, Up arrow, Enter).
As Op, run POST /v1/notifications/{id}/requeue. Expect 200.
Wait about ten seconds, then GET /v1/notifications/{id} again. Expect succeeded with six attempts (five failures, then one success). Bonus: check Mailpit at http://localhost:8025, where the email should now be waiting.
audit-trail-example.json: as Op, run GET /v1/notifications/{id}/audit. You should read the whole life: created, the retries, dead, requeued, succeeded. Click Download and save it as evidence/audit-trail-example.json.
Phase 5: File and verify
In the Files app, drag all the screenshots from Downloads into notifyhub/evidence/screenshots/.