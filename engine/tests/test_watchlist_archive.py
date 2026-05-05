"""V3 P6.4 — air-gapped watchlist archive import."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the scripts package is importable from tests.
ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from scripts import import_watchlist_archive as archive  # noqa: E402
from app.screening.sources import ofac, uk_ofsi, un  # noqa: E402


def test_classify_sdn_xml_picks_ofac(tmp_path: Path) -> None:
    path = tmp_path / "ofac-2026-05.sdn.xml"
    path.write_text("<x/>")
    parser, list_source = archive._classify(path)
    assert parser is ofac
    assert list_source == "OFAC"


def test_classify_consolidated_xml_picks_un(tmp_path: Path) -> None:
    path = tmp_path / "un-consolidated.xml"
    path.write_text("<x/>")
    parser, list_source = archive._classify(path)
    assert parser is un
    assert list_source == "UN"


def test_classify_uk_csv_picks_uk_ofsi(tmp_path: Path) -> None:
    path = tmp_path / "UK-Sanctions-List.csv"
    path.write_text("name\n")
    parser, list_source = archive._classify(path)
    assert parser is uk_ofsi
    assert list_source == "UK_OFSI"


def test_classify_unknown_filename_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "random.txt"
    path.write_text("nope")
    assert archive._classify(path) is None


def test_classify_is_case_insensitive(tmp_path: Path) -> None:
    path = tmp_path / "OFAC-SDN.XML"
    path.write_text("<x/>")
    parser, list_source = archive._classify(path)
    assert list_source == "OFAC"


def test_dry_run_does_not_call_upsert(monkeypatch, tmp_path: Path, capsys) -> None:
    """A --dry-run pass must never touch the DB."""
    called = {"hit": False}

    async def _boom(rows):
        called["hit"] = True
        return 0

    monkeypatch.setattr("scripts.import_watchlist_archive.upsert_batch", _boom)

    # Stub the OFAC parser to avoid needing a real SDN body.
    monkeypatch.setattr("scripts.import_watchlist_archive._parse_one", lambda p: ("OFAC", []))

    # Provide a recognisable file so it gets classified before _parse_one
    # (which we just monkeypatched). The classify logic runs first.
    path = tmp_path / "sdn.xml"
    path.write_text("<x/>")

    rc = archive.main(["--archive", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert called["hit"] is False
    captured = capsys.readouterr()
    assert "OFAC" in captured.out
    assert "dry-run" in captured.out


def test_main_errors_when_archive_missing(tmp_path: Path) -> None:
    rc = archive.main(["--archive", str(tmp_path / "nope")])
    assert rc == 2


def test_main_errors_when_archive_empty(tmp_path: Path) -> None:
    rc = archive.main(["--archive", str(tmp_path)])
    assert rc == 3


def test_main_errors_when_no_recognised_files(tmp_path: Path) -> None:
    (tmp_path / "random.txt").write_text("hi")
    rc = archive.main(["--archive", str(tmp_path)])
    assert rc == 5


def test_apply_summarises_per_source(monkeypatch, tmp_path: Path, capsys) -> None:
    """End-to-end: classify → parse stub → apply stub → print line per source."""
    sdn = tmp_path / "sdn.xml"
    sdn.write_text("<x/>")
    cons = tmp_path / "consolidated.xml"
    cons.write_text("<x/>")

    def fake_parse_one(path: Path):
        if "sdn" in path.name:
            return "OFAC", [object(), object(), object()]
        return "UN", [object()]

    async def fake_apply(rows):
        return len(rows)

    monkeypatch.setattr("scripts.import_watchlist_archive._parse_one", fake_parse_one)
    monkeypatch.setattr("scripts.import_watchlist_archive.upsert_batch", fake_apply)

    rc = archive.main(["--archive", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OFAC: ingested 3/3" in out
    assert "UN: ingested 1/1" in out


def test_parse_failure_returns_nonzero(monkeypatch, tmp_path: Path) -> None:
    sdn = tmp_path / "sdn.xml"
    sdn.write_text("<x/>")

    def boom(path: Path):
        raise RuntimeError("malformed")

    monkeypatch.setattr("scripts.import_watchlist_archive._parse_one", boom)
    rc = archive.main(["--archive", str(tmp_path)])
    assert rc == 4
