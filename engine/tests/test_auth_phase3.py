import asyncio

from fastapi.security import HTTPAuthorizationCredentials
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jose.utils import base64url_encode

import app.auth as auth_module


def test_get_current_user_prefers_database_profile_context(monkeypatch) -> None:
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(auth_module.settings, "supabase_url", None)
    monkeypatch.setattr(auth_module.settings, "kestrel_enable_demo_mode", False)

    async def fake_load_profile_context(user_id: str):
        assert user_id == "00000000-0000-0000-0000-000000000123"
        return {
            "org_id": "00000000-0000-0000-0000-000000000456",
            "org_type": "bank",
            "role": "manager",
            "persona": "bank_camlco",
            "designation": "Chief AML Compliance Officer",
        }

    monkeypatch.setattr(auth_module, "_load_profile_context", fake_load_profile_context)

    token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000123",
            "email": "camlco@example.com",
        },
        "test-secret",
        algorithm="HS256",
    )

    user = asyncio.run(
        auth_module.get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    )

    assert user.email == "camlco@example.com"
    assert user.org_type == "bank"
    assert user.role == "manager"
    assert user.persona == "bank_camlco"


def test_get_current_user_falls_back_to_token_claims_when_profile_lookup_missing(monkeypatch) -> None:
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(auth_module.settings, "supabase_url", None)
    monkeypatch.setattr(auth_module.settings, "kestrel_enable_demo_mode", False)

    async def fake_load_profile_context(user_id: str):
        return None

    monkeypatch.setattr(auth_module, "_load_profile_context", fake_load_profile_context)

    token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000789",
            "email": "analyst@example.com",
            "user_metadata": {
                "org_id": "00000000-0000-0000-0000-000000000999",
                "org_type": "regulator",
                "role": "analyst",
                "persona": "bfiu_analyst",
                "designation": "Deputy Director, Intelligence Analysis",
            },
        },
        "test-secret",
        algorithm="HS256",
    )

    user = asyncio.run(
        auth_module.get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    )

    assert user.org_id == "00000000-0000-0000-0000-000000000999"
    assert user.org_type == "regulator"
    assert user.role == "analyst"
    assert user.persona == "bfiu_analyst"


def test_get_current_user_accepts_jwks_signed_token(monkeypatch) -> None:
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", None)
    monkeypatch.setattr(auth_module.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(auth_module.settings, "supabase_jwks_url", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(auth_module.settings, "kestrel_enable_demo_mode", False)

    async def fake_load_profile_context(user_id: str):
        return {
            "org_id": "00000000-0000-0000-0000-000000000456",
            "org_type": "bank",
            "role": "manager",
            "persona": "bank_camlco",
            "designation": "Chief AML Compliance Officer",
        }

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwks_key = {
        "kid": "test-key",
        "alg": "RS256",
        "kty": "RSA",
        "use": "sig",
        "n": base64url_encode(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")).decode("utf-8"),
        "e": base64url_encode(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")).decode("utf-8"),
    }

    async def fake_get_jwks(force_refresh: bool = False):
        return [jwks_key]

    monkeypatch.setattr(auth_module, "_load_profile_context", fake_load_profile_context)
    monkeypatch.setattr(auth_module, "_get_jwks", fake_get_jwks)

    token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000123",
            "email": "camlco@example.com",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": 4102444800,
        },
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    user = asyncio.run(
        auth_module.get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    )

    assert user.email == "camlco@example.com"
    assert user.org_type == "bank"
    assert user.role == "manager"
