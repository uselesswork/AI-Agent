"""本机密码重置只影响指定账号，并撤销该账号所有会话。"""

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.database_schema import auth_sessions, users
from app.services.application_repository import ApplicationRepository
from app.services.auth_repository import AuthRepository
from scripts import reset_user_password

OLD_PASSWORD = "OriginalStrongPassphrase-A1"
NEW_PASSWORD = "AnotherStrongPassphrase-A2"
OTHER_PASSWORD = "OtherStrongPassphrase-B1"


def _accounts(tmp_path: Path):
    path = (tmp_path / "password-reset.db").as_posix()
    repository = ApplicationRepository(f"sqlite+pysqlite:///{path}")
    auth = AuthRepository(repository.engine)
    first_id = auth.create_user("owner_a", OLD_PASSWORD)
    other_id = auth.create_user("owner_b", OTHER_PASSWORD)
    return repository, auth, first_id, other_id


def test_reset_changes_only_target_password_and_revokes_its_sessions(tmp_path: Path) -> None:
    repository, auth, first_id, other_id = _accounts(tmp_path)
    first_token, _ = auth.create_session(first_id)
    another_first_token, _ = auth.create_session(first_id)
    other_token, _ = auth.create_session(other_id)

    auth.reset_password(" OWNER_A ", NEW_PASSWORD)

    assert auth.authenticate("owner_a", OLD_PASSWORD) is None
    assert auth.authenticate("owner_a", NEW_PASSWORD) == (first_id, "owner_a")
    assert auth.authenticate("owner_b", OTHER_PASSWORD) == (other_id, "owner_b")
    assert auth.session(first_token) is None
    assert auth.session(another_first_token) is None
    assert auth.session(other_token) is not None
    with repository.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(users)) == 2
        assert connection.scalar(select(func.count()).select_from(auth_sessions)) == 1


def test_unknown_account_or_invalid_password_leaves_login_unchanged(tmp_path: Path) -> None:
    _, auth, first_id, _ = _accounts(tmp_path)
    token, _ = auth.create_session(first_id)
    with pytest.raises(ValueError, match="账号不存在"):
        auth.reset_password("missing", NEW_PASSWORD)
    with pytest.raises(ValueError, match="12～128"):
        auth.reset_password("owner_a", "short")
    assert auth.authenticate("owner_a", OLD_PASSWORD) == (first_id, "owner_a")
    assert auth.session(token) is not None


def test_cli_requires_username_confirmation_and_never_prints_password(
    monkeypatch, tmp_path: Path, capsys,
) -> None:
    repository, auth, first_id, _ = _accounts(tmp_path)

    class Settings:
        @staticmethod
        def validated_database_url() -> str:
            return "sqlite+pysqlite:///test-only"

    monkeypatch.setattr(reset_user_password, "get_settings", Settings)
    monkeypatch.setattr(reset_user_password, "create_engine", lambda *_args, **_kwargs: repository.engine)
    answers = iter(["owner_a", "owner_a"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    passwords = iter([NEW_PASSWORD, NEW_PASSWORD])
    monkeypatch.setattr(reset_user_password, "getpass", lambda _prompt: next(passwords))
    assert reset_user_password.main() == 0
    assert NEW_PASSWORD not in capsys.readouterr().out
    assert auth.authenticate("owner_a", NEW_PASSWORD) == (first_id, "owner_a")


def test_cli_wrong_confirmation_does_not_prompt_for_password_or_update(
    monkeypatch, tmp_path: Path,
) -> None:
    repository, auth, first_id, _ = _accounts(tmp_path)

    class Settings:
        @staticmethod
        def validated_database_url() -> str:
            return "sqlite+pysqlite:///test-only"

    monkeypatch.setattr(reset_user_password, "get_settings", Settings)
    monkeypatch.setattr(reset_user_password, "create_engine", lambda *_args, **_kwargs: repository.engine)
    answers = iter(["owner_a", "different"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(reset_user_password, "getpass", lambda _prompt: pytest.fail(
        "确认失败后不应再读取密码",
    ))
    assert reset_user_password.main() == 1
    assert auth.authenticate("owner_a", OLD_PASSWORD) == (first_id, "owner_a")
