from pathlib import Path

from app.config import DEFAULT_ENV_FILES, ENGINE_ROOT, REPO_ROOT


def test_engine_settings_look_for_repo_and_engine_env_files() -> None:
    expected = (
        str(REPO_ROOT / ".env"),
        str(REPO_ROOT / ".env.local"),
        str(ENGINE_ROOT / ".env"),
        str(ENGINE_ROOT / ".env.local"),
    )

    assert DEFAULT_ENV_FILES == expected
    assert Path(DEFAULT_ENV_FILES[0]).name == ".env"
    assert Path(DEFAULT_ENV_FILES[2]).parts[-2:] == ("engine", ".env")
