import asyncio

from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

import app.auth as auth_module


def test_get_current_user_prefers_database_profile_context(monkeypatch) -> None:
    monkeypatch.setattr(auth_module.settings, "supabase_jwt_secret", "test-secret")
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
