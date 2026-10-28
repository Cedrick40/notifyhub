import uuid

from django.test import TestCase
from rest_framework.test import APIClient

from notifications.auth import generate_api_key, hash_api_key
from notifications.models import Client, Notification, NotificationAttempt


class AuthAndOwnershipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        raw_prod = generate_api_key()
        self.prod = Client.objects.create(name="producer1", api_key_hash=hash_api_key(raw_prod), role=Client.Role.PRODUCER)
        raw_op = generate_api_key()
        self.op = Client.objects.create(name="operator1", api_key_hash=hash_api_key(raw_op), role=Client.Role.OPERATOR)
        self.raw_prod = raw_prod
        self.raw_op = raw_op

    def test_missing_auth_returns_401(self):
        resp = self.client.post("/v1/notifications", {}, format="json")
        self.assertIn(resp.status_code, [401])

    def test_producer_can_submit_and_view_own(self):
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        payload = {"channel": "email", "recipient": "test@example.com", "payload": {"subject": "Hi", "body": "Hello"}}
        resp = self.client.post("/v1/notifications", payload, format="json", HTTP_IDEMPOTENCY_KEY="key1")
        self.assertEqual(resp.status_code, 202)
        nid = resp.data["id"]
        resp2 = self.client.get(f"/v1/notifications/{nid}")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["id"], nid)

    def test_producer_cannot_see_others(self):
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        payload = {"channel": "sms", "recipient": "+12345678", "payload": {"body": "Hi"}}
        resp = self.client.post("/v1/notifications", payload, format="json", HTTP_IDEMPOTENCY_KEY="k2")
        nid = resp.data["id"]
        # different producer
        raw_p2 = generate_api_key()
        p2 = Client.objects.create(name="producer2", api_key_hash=hash_api_key(raw_p2), role=Client.Role.PRODUCER)
        self.client.credentials(HTTP_X_API_KEY=raw_p2)
        resp3 = self.client.get(f"/v1/notifications/{nid}")
        self.assertEqual(resp3.status_code, 404)


class IdempotencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        raw_prod = generate_api_key()
        self.prod = Client.objects.create(name="producer", api_key_hash=hash_api_key(raw_prod), role=Client.Role.PRODUCER)
        self.raw_prod = raw_prod

    def test_same_idempotency_key_same_response(self):
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        payload = {"channel": "push", "recipient": "device-1", "payload": {"title": "T", "body": "B"}}
        resp1 = self.client.post("/v1/notifications", payload, format="json", HTTP_IDEMPOTENCY_KEY="idem1")
        resp2 = self.client.post("/v1/notifications", payload, format="json", HTTP_IDEMPOTENCY_KEY="idem1")
        self.assertEqual(resp1.status_code, 202)
        self.assertEqual(resp2.status_code, 202)
        self.assertEqual(resp1.data["id"], resp2.data["id"])
        self.assertEqual(Notification.objects.filter(client=self.prod).count(), 1)


class ValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        raw_prod = generate_api_key()
        self.prod = Client.objects.create(name="producer", api_key_hash=hash_api_key(raw_prod), role=Client.Role.PRODUCER)
        self.raw_prod = raw_prod

    def test_invalid_email(self):
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        payload = {"channel": "email", "recipient": "not-an-email", "payload": {"subject": "Hi", "body": "Hello"}}
        resp = self.client.post("/v1/notifications", payload, format="json", HTTP_IDEMPOTENCY_KEY="v1")
        self.assertEqual(resp.status_code, 400)

    def test_missing_idempotency_key(self):
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        payload = {"channel": "email", "recipient": "test@example.com", "payload": {"subject": "Hi", "body": "Hello"}}
        resp = self.client.post("/v1/notifications", payload, format="json")
        self.assertEqual(resp.status_code, 400)


class OperatorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        raw_prod = generate_api_key()
        self.prod = Client.objects.create(name="producer", api_key_hash=hash_api_key(raw_prod), role=Client.Role.PRODUCER)
        raw_op = generate_api_key()
        self.op = Client.objects.create(name="operator", api_key_hash=hash_api_key(raw_op), role=Client.Role.OPERATOR)
        self.raw_prod = raw_prod
        self.raw_op = raw_op

    def test_producer_cannot_requeue(self):
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        payload = {"channel": "email", "recipient": "test@example.com", "payload": {"subject": "Hi", "body": "Hello"}}
        resp = self.client.post("/v1/notifications", payload, format="json", HTTP_IDEMPOTENCY_KEY="op1")
        nid = resp.data["id"]
        # make it dead
        n = Notification.objects.get(id=nid)
        n.status = Notification.Status.DEAD
        n.save()
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        r = self.client.post(f"/v1/notifications/{nid}/requeue")
        self.assertIn(r.status_code, [401, 403])

    def test_operator_can_requeue_dead(self):
        self.client.credentials(HTTP_X_API_KEY=self.raw_prod)
        payload = {"channel": "email", "recipient": "test@example.com", "payload": {"subject": "Hi", "body": "Hello"}}
        resp = self.client.post("/v1/notifications", payload, format="json", HTTP_IDEMPOTENCY_KEY="op2")
        nid = resp.data["id"]
        n = Notification.objects.get(id=nid)
        n.status = Notification.Status.DEAD
        n.save()
        self.client.credentials(HTTP_X_API_KEY=self.raw_op)
        r = self.client.post(f"/v1/notifications/{nid}/requeue")
        self.assertEqual(r.status_code, 200)
        n.refresh_from_db()
        self.assertEqual(n.status, Notification.Status.QUEUED)
