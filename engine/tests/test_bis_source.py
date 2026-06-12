"""Pure-parse coverage for the BIS / trade.gov CSL adapter.

No network: feeds the parser an in-memory CSV mirroring the documented
27-column CSL schema and asserts the BIS-filtering + field mapping. The
load-bearing risk is (a) NOT double-ingesting OFAC SDN rows that live in
the same file, and (b) correctly tagging which BIS sublist fired.
"""
from __future__ import annotations

import csv
import io
from datetime import date

from app.screening.sources import bis

_COLUMNS = [
    "source", "entity_number", "type", "programs", "name", "title", "addresses",
    "federal_register_notice", "start_date", "end_date", "standard_order",
    "license_requirement", "license_policy", "call_sign", "vessel_type",
    "gross_tonnage", "gross_registered_tonnage", "vessel_flag", "vessel_owner",
    "remarks", "source_list_url", "alt_names", "citizenships", "dates_of_birth",
    "nationalities", "places_of_birth", "source_information_url",
]


def _csv(*rows: dict[str, str]) -> bytes:
    """Build a CSL-shaped CSV with proper quoting (values may contain commas)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in _COLUMNS})
    return buf.getvalue().encode("utf-8")


def _row(**over: str) -> dict[str, str]:
    return dict(over)


def test_keeps_entity_list_drops_sdn_and_state_lists() -> None:
    content = _csv(
        _row(source="EL", type="", name="Meridian Precision Instruments Co", nationalities="China"),
        _row(source="SDN", type="individual", name="Some OFAC Person"),   # OFAC — must be dropped
        _row(source="DTC", type="entity", name="State Dept Debarred Co"),  # State — must be dropped
        _row(source="ISN", type="entity", name="Nonproliferation Co"),     # State — must be dropped
        _row(source="DPL", type="individual", name="Viktor Sorokin"),
        _row(source="UVL", type="", name="Orient Tech Sourcing FZE"),
    )
    entries = bis.parse(content)
    names = {e.primary_name for e in entries}
    assert names == {
        "Meridian Precision Instruments Co",
        "Viktor Sorokin",
        "Orient Tech Sourcing FZE",
    }
    assert all(e.list_source == "BIS" for e in entries)


def test_sublist_label_flows_into_reason() -> None:
    content = _csv(
        _row(source="EL", name="Crescent Advanced Materials Ltd", license_requirement="all items"),
        _row(source="DPL", name="Viktor Sorokin"),
        _row(source="UVL", name="Orient Tech Sourcing FZE"),
    )
    by_name = {e.primary_name: e for e in bis.parse(content)}
    assert by_name["Crescent Advanced Materials Ltd"].reason.startswith("BIS Entity List")
    assert "licence: all items" in by_name["Crescent Advanced Materials Ltd"].reason
    assert by_name["Viktor Sorokin"].reason.startswith("BIS Denied Persons List")
    assert by_name["Orient Tech Sourcing FZE"].reason.startswith("BIS Unverified List")


def test_entry_type_defaults_to_entity_for_blank_type() -> None:
    content = _csv(
        _row(source="EL", type="", name="Some Company Co"),
        _row(source="DPL", type="Individual", name="A Person"),
        _row(source="SDN", type="vessel", name="Should Be Dropped"),
    )
    by_name = {e.primary_name: e for e in bis.parse(content)}
    assert by_name["Some Company Co"].entry_type == "entity"
    assert by_name["A Person"].entry_type == "individual"


def test_semicolon_fields_split_into_lists() -> None:
    content = _csv(
        _row(
            source="EL",
            name="Meridian Precision Instruments Co",
            alt_names="Meridian Precision; MPI Co",
            addresses="Shenzhen, China; Hong Kong",
            nationalities="China",
        ),
    )
    entry = bis.parse(content)[0]
    assert entry.aliases == ["Meridian Precision", "MPI Co"]
    assert [a["address1"] for a in entry.addresses] == ["Shenzhen, China", "Hong Kong"]
    assert entry.nationality == "China"


def test_dates_of_birth_first_value_parsed() -> None:
    content = _csv(
        _row(source="DPL", type="individual", name="Viktor Sorokin", dates_of_birth="11 Feb 1974; 1975"),
    )
    entry = bis.parse(content)[0]
    assert entry.date_of_birth == date(1974, 2, 11)


def test_full_label_source_is_recognised_as_bis() -> None:
    # Some CSL distributions ship the long label instead of the short code.
    content = _csv(
        _row(source="Entity List (EL) - Bureau of Industry and Security", name="Labelled Co"),
        _row(source="Specially Designated Nationals (SDN) - Treasury", name="Drop Me"),
    )
    entries = bis.parse(content)
    assert [e.primary_name for e in entries] == ["Labelled Co"]
    assert entries[0].reason.startswith("BIS Entity List")


def test_blank_name_row_skipped() -> None:
    content = _csv(_row(source="EL", name=""), _row(source="EL", name="Real Co"))
    assert [e.primary_name for e in bis.parse(content)] == ["Real Co"]


def test_raw_record_carries_provenance() -> None:
    content = _csv(
        _row(source="EL", entity_number="", name="Meridian Precision Instruments Co",
             source_list_url="https://www.bis.doc.gov/entity-list"),
    )
    entry = bis.parse(content)[0]
    assert entry.raw_record["source_code"] == "EL"
    assert entry.raw_record["sublist"] == "BIS Entity List"
    assert entry.raw_record["source_list_url"] == "https://www.bis.doc.gov/entity-list"


def test_identifiers_empty_for_csl_csv() -> None:
    # The delimited CSL file has no passport/NID columns — identifiers stay {}.
    content = _csv(_row(source="DPL", type="individual", name="Viktor Sorokin"))
    assert bis.parse(content)[0].identifiers == {}


def test_empty_feed_yields_no_entries() -> None:
    assert bis.parse(_csv()) == []
