import hashlib
import secrets

from rest_framework import authentication, exceptions

from .models import Client


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class ApiKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        raw_key = request.headers.get("X-API-Key")
        if not raw_key:
            return None  # no credentials supplied; permissions will reject
        try:
            client = Client.objects.get(api_key_hash=hash_api_key(raw_key))
        except Client.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key.")
        return (client, None)

    def authenticate_header(self, request):
        return "X-API-Key"