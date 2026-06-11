"""Pure-helper coverage for the cloud migration runner (scripts/apply_migrations.py)."""
from __future__ import annotations

from pathlib import Path

from scripts.apply_migrations import resolve_migrations_dir, version_from_filename


def test_version_from_filename_leading_digits() -> None:
    assert version_from_filename("029_bank_signup_requests.sql") == "029"
    assert version_from_filename("001_schema.sql") == "001"


def test_version_from_filename_without_digit_prefix_falls_back_to_stem() -> None:
    assert version_from_filename("hotfix.sql") == "hotfix"


def test_resolve_migrations_dir_finds_repo_migrations() -> None:
    resolved = resolve_migrations_dir()
    assert resolved.name == "migrations"
    assert (resolved / "001_schema.sql").is_file()
    assert (resolved / "029_bank_signup_requests.sql").is_file()


def test_resolve_migrations_dir_env_override(monkeypatch) -> None:
    monkeypatch.setenv("KESTREL_MIGRATIONS_DIR", "/tmp/custom")
    assert resolve_migrations_dir() == Path("/tmp/custom")
