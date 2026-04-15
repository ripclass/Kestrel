import uuid
from types import SimpleNamespace

import pytest

from app.core.pipeline import run_str_pipeline
from app.models.connection import Connection
from app.models.entity import Entity


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
    def __init__(self) -> None:
        self.added: list[object] = []

    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        return FakeExecResult([])

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_run_str_pipeline_resolves_entities_without_cross_bank_match() -> None:
    org_id = uuid.uuid4()
    session = FakeSession()
    report = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        subject_name="Rizwana Enterprise",
        subject_account="1781430000701",
        subject_bank="DBBL",
        subject_phone=None,
        subject_wallet=None,
        subject_nid=None,
        matched_entity_ids=[],
        cross_bank_hit=False,
        auto_risk_score=None,
    )

    result = await run_str_pipeline(session, str_report=report, org_id=org_id)

    assert len(result["entities"]) >= 1
    assert result["matches"] == []
    assert result["alerts"] == []
    assert report.cross_bank_hit is False
    assert len(report.matched_entity_ids) >= 1

    added_entities = [obj for obj in session.added if isinstance(obj, Entity)]
    assert len(added_entities) >= 1
