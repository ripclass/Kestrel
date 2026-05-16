"""Static-shape checks on the 29 TBML avenue seed rows in migration 026.

Reads the migration SQL file directly, parses the INSERT statement, and
verifies (1) all 29 rows are present, (2) every row uses an MLPA §2(cc)
predicate code, (3) BFIU avenue refs follow the §2.4.1.x / §2.4.2.x / §2.5
pattern. No DB connection — the migration file is the source of truth.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from app.schemas.predicate_offence import PREDICATE_OFFENCES

MIGRATION = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "026_tbml_avenues_seed.sql"
TBML_AVENUE_ROW = re.compile(
    r"\('(?P<id>tbml-avenue-[^']+)',[^']*'(?P<title>[^']+)',[^']*'(?P<category>[a-z_]+)'"
    r".*?ARRAY\[(?P<predicates>[^\]]*)\]::text\[\],\s*'(?P<ref>[^']+)'\)",
    re.DOTALL,
)


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str | list[str]]]:
    text = MIGRATION.read_text(encoding="utf-8")
    parsed: list[dict[str, str | list[str]]] = []
    for match in TBML_AVENUE_ROW.finditer(text):
        parsed.append(
            {
                "id": match.group("id"),
                "title": match.group("title"),
                "category": match.group("category"),
                "predicates": [
                    value.strip().strip("'") for value in match.group("predicates").split(",")
                ],
                "ref": match.group("ref"),
            }
        )
    return parsed


def test_exactly_29_tbml_avenue_rows(rows) -> None:
    assert len(rows) == 29, f"expected 29 TBML avenue rows in migration 026, got {len(rows)}"


def test_14_import_14_export_1_royalty(rows) -> None:
    imports = [row for row in rows if row["id"].startswith("tbml-avenue-import-")]
    exports = [row for row in rows if row["id"].startswith("tbml-avenue-export-")]
    royalty = [row for row in rows if row["id"].startswith("tbml-avenue-royalty-")]
    assert len(imports) == 14
    assert len(exports) == 14
    assert len(royalty) == 1


def test_every_row_uses_tbml_category(rows) -> None:
    for row in rows:
        assert row["category"] == "tbml", f"{row['id']} should be category=tbml"


def test_every_predicate_in_mlpa_2cc_schedule(rows) -> None:
    canon = set(PREDICATE_OFFENCES)
    for row in rows:
        for code in row["predicates"]:
            assert code in canon, f"{row['id']} cites unknown predicate {code!r}"


def test_every_bfiu_avenue_ref_matches_section_pattern(rows) -> None:
    # Acceptable refs: 2.4.1.i..xiv, 2.4.2.i..xiv, 2.5
    pattern = re.compile(r"^(2\.4\.[12]\.(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv)|2\.5)$")
    for row in rows:
        assert pattern.match(row["ref"]), f"{row['id']} has malformed BFIU ref {row['ref']!r}"


def test_every_row_cites_at_least_one_predicate(rows) -> None:
    # The 29 avenues are TBML-specific; every row must cite at least
    # smuggling_customs_excise (§2(cc)(18)) or tax_related_offences (§2(cc)(19))
    # or one of the supporting predicates (fraud, forgery, smuggling_currency).
    expected = {
        "smuggling_customs_excise",
        "tax_related_offences",
        "fraud",
        "forgery",
        "smuggling_currency",
        "black_marketing",
        "infringement_intellectual_property",
    }
    for row in rows:
        intersect = set(row["predicates"]) & expected
        assert intersect, f"{row['id']} cites no TBML-style predicate: {row['predicates']}"
