import uuid
from types import SimpleNamespace

import pytest

from app.core.resolver import (
    normalize_identifier,
    resolve_identifier,
    resolve_identifiers_from_str,
)
from app.models.connection import Connection
from app.models.entity import Entity


@pytest.mark.parametrize(
    ("entity_type", "raw", "expected"),
    [
        ("account", "  1781 4300 0070 1  ", "1781430000701"),
        ("account", "abc-123", "ABC123"),
        ("phone", "+880 1712 345678", "+8801712345678"),
        ("phone", "01712-345678", "01712345678"),
        ("phone", "8801712345678", "+8801712345678"),
        ("nid", " 1234 5678 9012 ", "123456789012"),
        ("wallet", " abcd1234 ", "ABCD1234"),
        ("person", "  Rizwana   Enterprise  ", "rizwana enterprise"),
        ("business", "RIZWANA ENTERPRISE LTD.", "rizwana enterprise ltd."),
    ],
)
def test_normalize_identifier_forms(entity_type: str, raw: str, expected: str) -> None:
    assert normalize_identifier(entity_type, raw) == expected


def test_normalize_identifier_rejects_empty() -> None:
    with pytest.raises(ValueError):
        normalize_identifier("account", "")
    with pytest.raises(ValueError):
        normalize_identifier("account", "   ")


def test_normalize_identifier_unknown_type_passes_through() -> None:
    assert normalize_identifier("device", "  ABC-XYZ  ") == "abc-xyz"


class FakeScalarsResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def first(self) -> object | None:
        return self._items[0] if self._items else None

    def all(self) -> list[object]:
        return list(self._items)


class FakeExecResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._items)


class FakeSession:
    def __init__(self, preloaded: list[object] | None = None) -> None:
        self.preloaded = preloaded or []
        self.added: list[object] = []
        self.flushed = False

    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        return FakeExecResult(self.preloaded)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_resolve_identifier_creates_new_entity_when_no_match() -> None:
    session = FakeSession(preloaded=[])
    org_id = uuid.uuid4()

    entity = await resolve_identifier(
        session,
        entity_type="account",
        raw_value="  1781 4300 0070 1  ",
        org_id=org_id,
        source="str_cross_ref",
        display_name="Rizwana Enterprise",
    )

    assert entity.canonical_value == "1781430000701"
    assert entity.entity_type == "account"
    assert entity.source == "str_cross_ref"
    assert float(entity.confidence) == pytest.approx(0.7)
    assert org_id in entity.reporting_orgs
    assert entity.report_count == 1
    assert session.added == [entity]
    assert session.flushed is True


@pytest.mark.asyncio
async def test_resolve_identifier_updates_existing_entity_on_hit() -> None:
    existing = Entity(
        id=uuid.uuid4(),
        entity_type="phone",
        canonical_value="+8801712345678",
        display_value="01712345678",
        display_name="Rizwana",
        confidence=0.6,
        source="system",
        reporting_orgs=[],
        report_count=2,
        total_exposure=0,
        tags=[],
        metadata_json={},
    )
    new_org_id = uuid.uuid4()
    session = FakeSession(preloaded=[existing])

    entity = await resolve_identifier(
        session,
        entity_type="phone",
        raw_value="+880 1712-345678",
        org_id=new_org_id,
        source="str_cross_ref",
        display_name="Rizwana",
    )

    assert entity is existing
    assert entity.report_count == 3
    assert new_org_id in entity.reporting_orgs
    assert entity.last_seen is not None
    assert session.added == []


class FakeSessionWithEmptyLookups(FakeSession):
    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        return FakeExecResult([])


@pytest.mark.asyncio
async def test_resolve_identifiers_from_str_creates_all_entities_and_connections() -> None:
    session = FakeSessionWithEmptyLookups(preloaded=[])
    org_id = uuid.uuid4()

    report = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        subject_name="Rizwana Enterprise",
        subject_account="178143000701",
        subject_bank="Dutch-Bangla Bank PLC",
        subject_phone="+8801712345678",
        subject_wallet=None,
        subject_nid="1234567890123",
    )

    entities = await resolve_identifiers_from_str(
        session, str_report=report, org_id=org_id
    )

    types = sorted({e.entity_type for e in entities})
    assert "account" in types
    assert "phone" in types
    assert "nid" in types

    added_entities = [obj for obj in session.added if isinstance(obj, Entity)]
    added_connections = [obj for obj in session.added if isinstance(obj, Connection)]

    # 3 non-person identifiers (account, phone, nid) + person slot = 4 entities
    assert len(added_entities) == 4
    # 3 graph entities pair into 3 unordered pairs = 6 directed edges
    assert len(added_connections) == 6
    assert all(conn.relation == "same_owner" for conn in added_connections)
