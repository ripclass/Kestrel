from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_rules_policy_declares_with_check_in_base_schema() -> None:
    schema_sql = (REPO_ROOT / "supabase" / "migrations" / "001_schema.sql").read_text(encoding="utf-8")

    assert "create policy rules_org on rules" in schema_sql
    assert "with check (org_id = auth_org_id() or is_system = true);" in schema_sql


def test_rules_policy_fix_exists_for_existing_environments() -> None:
    migration_sql = (REPO_ROOT / "supabase" / "migrations" / "002_rules_insert_policy.sql").read_text(
        encoding="utf-8"
    )

    assert "drop policy if exists rules_org on rules;" in migration_sql
    assert "create policy rules_org on rules" in migration_sql
    assert "with check (org_id = auth_org_id() or is_system = true);" in migration_sql
