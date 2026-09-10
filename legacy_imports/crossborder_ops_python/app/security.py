from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import jwt
from jwt import PyJWKClient


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_access_token(payload: dict[str, Any], secret: str, ttl_seconds: int = 3600) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl_seconds
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = _b64(raw)
    sig = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64(sig)}"


def verify_access_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        encoded, sig = token.split(".", 1)
        expected = _b64(hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        body = json.loads(_unb64(encoded))
        if int(body.get("exp", 0)) < int(time.time()):
            return None
        return body
    except Exception:
        return None


def verify_request_token(token: str, settings) -> dict[str, Any] | None:
    provider = getattr(settings, "identity_provider", "local")
    if provider in {"oidc", "jwt"}:
        return verify_oidc_token(token, getattr(settings, "oidc_jwks_url", ""), getattr(settings, "oidc_audience", ""), getattr(settings, "oidc_issuer", ""))
    return verify_access_token(token, getattr(settings, "auth_secret", ""))


def verify_oidc_token(token: str, jwks_url: str, audience: str, issuer: str) -> dict[str, Any] | None:
    if not jwks_url or not audience or not issuer:
        return None
    try:
        signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=["RS256", "ES256"], audience=audience, issuer=issuer)
    except Exception:
        return None
