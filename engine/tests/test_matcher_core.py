import uuid
from types import SimpleNamespace

import pytest

from app.core.matcher import run_cross_bank_matching
from app.models.entity import Entity
from app.models.match import Match


class FakeScalarsResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def first(self) -> object | None:
        return self._items[0] if self._items else None


class FakeExecResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._items)


class FakeSession:
    def __init__(self, existing_match: Match | None = None) -> None:
        self.added: list[object] = []
        self.existing_match = existing_match

    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        return FakeExecResult([self.existing_match] if self.existing_match else [])

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def make_entity(*, reporting_orgs: list[uuid.UUID], total_exposure: float = 500_000) -> Entity:
    return Entity(
        id=uuid.uuid4(),
        entity_type="account",
        canonical_value="1781430000701",
        display_value="1781430000701",
        display_name="Rizwana",
        confidence=0.7,
        source="str_cross_ref",
        reporting_orgs=reporting_orgs,
        report_count=len(reporting_orgs),
        total_exposure=total_exposure,
        tags=[],
        metadata_json={},
    )


@pytest.mark.asyncio
async def test_matcher_creates_match_when_two_orgs_report_entity() -> None:
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    entity = make_entity(reporting_orgs=[org_a, org_b])
    session = FakeSession()
    str_report = SimpleNamespace(id=uuid.uuid4(), subject_bank="Bank A", subject_account="1781430000701")

    matches, alerts = await run_cross_bank_matching(
        session,
        entities=[entity],
        str_report=str_report,
        org_id=org_a,
    )

    assert len(matches) == 1
    match = matches[0]
    assert match.match_type == "account"
    assert match.match_key == "1781430000701"
    assert set(match.involved_org_ids) == {org_a, org_b}
    assert match.match_count == 2
    assert match.risk_score >= 50
    assert len(alerts) == 1
    assert alerts[0].source_type == "cross_bank"
    assert alerts[0].alert_type == "cross_bank_match"


@pytest.mark.asyncio
async def test_matcher_skips_entity_reported_by_single_org() -> None:
    single_org = uuid.uuid4()
    entity = make_entity(reporting_orgs=[single_org])
    session = FakeSession()
    str_report = SimpleNamespace(id=uuid.uuid4(), subject_bank="Bank A", subject_account="X")

    matches, alerts = await run_cross_bank_matching(
        session, entities=[entity], str_report=str_report, org_id=single_org
    )

    assert matches == []
    assert alerts == []


@pytest.mark.asyncio
async def test_matcher_scales_score_with_match_count_and_exposure() -> None:
    orgs = [uuid.uuid4() for _ in range(4)]
    entity = make_entity(reporting_orgs=orgs, total_exposure=15_000_000)
    session = FakeSession()
    str_report = SimpleNamespace(id=uuid.uuid4(), subject_bank="Bank A", subject_account="X")

    matches, alerts = await run_cross_bank_matching(
        session, entities=[entity], str_report=str_report, org_id=orgs[0]
    )

    assert len(matches) == 1
    # score = 50 + 10*4 + 20 (exposure > 10M) = 110 -> clamped to 100
    assert matches[0].risk_score == 100
    assert matches[0].severity == "critical"
