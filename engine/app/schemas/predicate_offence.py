"""Predicate offences as defined by MLPA 2012 §2(cc) (migration 025).

Single source of truth shared by STR / Case / Dissemination schemas. Keep in
sync with the CHECK constraint in `supabase/migrations/025_predicate_offences.sql`
and with `web/src/types/domain.ts::PredicateOffence`.

The 28 categories are an exact transcription of MLPA 2012 §2(cc) clauses
(1) through (28); the catch-all (28) "other_bb_gazetted" covers offences
declared as predicate by Bangladesh Bank via Gazette notification.
"""
from __future__ import annotations

from typing import Literal

PredicateOffence = Literal[
    "corruption_and_bribery",
    "counterfeiting_currency",
    "counterfeiting_deeds_and_documents",
    "extortion",
    "fraud",
    "forgery",
    "illegal_trade_firearms",
    "illegal_trade_narcotics",
    "illegal_trade_stolen_goods",
    "kidnapping_restraint_hostage",
    "murder_grievous_injury",
    "trafficking_women_children",
    "black_marketing",
    "smuggling_currency",
    "theft_robbery_dacoity_piracy_hijacking",
    "human_trafficking",
    "dowry",
    "smuggling_customs_excise",
    "tax_related_offences",
    "infringement_intellectual_property",
    "terrorism_or_terrorist_financing",
    "adulteration_title_infringement",
    "environmental_offences",
    "sexual_exploitation",
    "insider_trading_market_manipulation",
    "organized_crime",
    "racketeering",
    "other_bb_gazetted",
]

# Tuple form for runtime introspection (e.g. building admin dropdowns,
# validating array members in tests).
PREDICATE_OFFENCES: tuple[str, ...] = PredicateOffence.__args__  # type: ignore[attr-defined]
