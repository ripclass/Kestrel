"""Coverage-reporting helper for the screening surface.

Pins that get_screening_coverage classifies sources into active (has rows) vs
expected-but-empty, and reflects adverse-media config — the data behind the
'screened against these lists; EU/adverse-media not active' UI message that
stops an empty result reading as a false all-clear.
"""
from __future__ import annotations

import pytest

from app.services.screening import _EXPECTED_WATCHLIST_SOURCES


def test_bis_is_an_expected_source() -> None:
    # BIS was added as a real source; coverage must account for it.
    assert "BIS" in _EXPECTED_WATCHLIST_SOURCES


def test_expected_sources_are_the_known_seven() -> None:
    assert set(_EXPECTED_WATCHLIST_SOURCES) == {
        "OFAC", "UN", "UK_OFSI", "BIS", "EU", "BB_DOMESTIC", "PEP",
    }


def test_bis_is_a_valid_list_source_for_filter_and_upload() -> None:
    # Regression: _VALID_LIST_SOURCES omitted BIS, so /screening/entries?list_source=BIS
    # and manual BIS uploads 422'd even though BIS entries existed.
    from app.schemas.screening import list_source_is_supported

    assert list_source_is_supported("BIS") is True
    assert list_source_is_supported("bis") is True


@pytest.mark.asyncio
async def test_get_screening_coverage_classifies_active_vs_inactive() -> None:
    """Drive the coverage helper with a fake session whose grouped-count query
    returns OFAC + BIS populated and everything else empty."""
    from app.services import adverse_media as am
    from app.services import screening as screening_module

    class _FakeResult:
        def all(self):
            return [("OFAC", 19000), ("BIS", 4)]

    class _FakeSession:
        async def execute(self, _stmt):
            return _FakeResult()

    # Force adverse-media to look unconfigured regardless of local env.
    saved = am.is_provider_configured
    am.is_provider_configured = lambda: False
    try:
        payload = await screening_module.get_screening_coverage(_FakeSession())
    finally:
        am.is_provider_configured = saved

    active = {row["source"]: row["count"] for row in payload["active_sources"]}
    assert active == {"BIS": 4, "OFAC": 19000}
    # EU/UN/UK_OFSI/BB_DOMESTIC/PEP are expected but empty in this fake.
    assert set(payload["inactive_sources"]) == {"UN", "UK_OFSI", "EU", "BB_DOMESTIC", "PEP"}
    assert payload["adverse_media"] == {"configured": False, "provider": "stub"}
    assert payload["total_entries"] == 19004
