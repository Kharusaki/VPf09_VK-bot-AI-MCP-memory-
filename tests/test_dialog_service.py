"""Тесты операций с профилем и диалогами."""

from __future__ import annotations

import pytest

from models.enums import Mode
from models.user import UserProfile
from services.dialog_service import DialogService
from utils.errors import DialogLimitError, DialogNotFoundError, LastDialogError
from utils.time import utc_now

from .conftest import make_settings


class MemoryStorage:
    """Минимальная замена MCP-репозитория для тестов сервиса."""

    def __init__(self) -> None:
        self.users: dict[int, UserProfile] = {}

    async def load_user(self, user_id: int) -> UserProfile | None:
        return self.users.get(int(user_id))

    async def save_user(self, profile: UserProfile) -> None:
        self.users[int(profile.user_id)] = profile


@pytest.fixture()
def service() -> tuple[DialogService, MemoryStorage]:
    storage = MemoryStorage()
    return DialogService(storage=storage, settings=make_settings(max_dialogs=3)), storage


async def test_get_profile_creates_first_dialog(service) -> None:
    dialogs, storage = service
    profile = await dialogs.get_profile(42, "Иван")

    assert profile.user_id == 42
    assert profile.display_name == "Иван"
    assert len(profile.dialogs) == 1
    assert profile.active_dialog is not None
    assert profile.active_dialog.title == "Диалог 1"
    assert profile.active_dialog.mode is Mode.ASSISTANT
    assert profile.dialog_counter == 2
    assert 42 in storage.users


async def test_get_profile_updates_display_name(service) -> None:
    dialogs, _ = service
    await dialogs.get_profile(42, "Иван")
    profile = await dialogs.get_profile(42, "Пётр")

    assert profile.display_name == "Пётр"
    assert len(profile.dialogs) == 1


async def test_new_dialog_increments_title_and_activates(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)

    second = dialogs.new_dialog(profile)
    await dialogs.save(profile)

    assert second.title == "Диалог 2"
    assert profile.active_dialog_id == second.id
    assert len(profile.dialogs) == 2


async def test_dialog_limit(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)
    dialogs.new_dialog(profile)
    dialogs.new_dialog(profile)

    with pytest.raises(DialogLimitError):
        dialogs.new_dialog(profile)


async def test_switch_and_delete_dialog(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)
    first = profile.dialogs[0]
    second = dialogs.new_dialog(profile)

    assert dialogs.switch_dialog(profile, first.id) is first
    assert profile.active_dialog_id == first.id

    title = dialogs.delete_dialog(profile, first.id)
    assert title == "Диалог 1"
    assert profile.active_dialog_id == second.id
    assert [dialog.id for dialog in profile.dialogs] == [second.id]


async def test_cannot_delete_last_dialog(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)

    with pytest.raises(LastDialogError):
        dialogs.delete_dialog(profile, profile.dialogs[0].id)


async def test_delete_unknown_dialog(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)
    dialogs.new_dialog(profile)

    with pytest.raises(DialogNotFoundError):
        dialogs.delete_dialog(profile, "missing")


async def test_rename_dialog_normalizes_and_truncates(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)
    dialog = profile.dialogs[0]

    renamed = dialogs.rename_dialog(profile, dialog.id, "  Новое   имя  ")
    assert renamed.title == "Новое имя"

    long = dialogs.rename_dialog(profile, dialog.id, "x" * 80)
    assert long.title == "x" * 50

    with pytest.raises(ValueError):
        dialogs.rename_dialog(profile, dialog.id, "   ")


async def test_clear_dialog_keeps_dialog_and_mode(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)
    dialog = profile.dialogs[0]
    dialogs.set_mode(profile, Mode.PROGRAMMER, dialog.id)

    cleared = dialogs.clear_dialog(profile, dialog.id)

    assert cleared is dialog
    assert cleared.mode is Mode.PROGRAMMER
    assert cleared.message_count == 0
    assert cleared.updated_at >= dialog.created_at


async def test_set_mode_changes_only_active_dialog(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)
    first = profile.dialogs[0]
    second = dialogs.new_dialog(profile, mode=Mode.FRIEND)

    dialogs.set_mode(profile, Mode.BUSINESS, first.id)

    assert first.mode is Mode.BUSINESS
    assert second.mode is Mode.FRIEND
    assert profile.active_dialog_id == second.id


async def test_get_profile_repairs_missing_active_dialog(service) -> None:
    dialogs, storage = service
    profile = await dialogs.get_profile(1)
    profile.active_dialog_id = "missing"
    storage.users[1] = profile

    repaired = await dialogs.get_profile(1)

    assert repaired.active_dialog_id == repaired.dialogs[0].id


async def test_with_mode_returns_copy(service) -> None:
    dialogs, _ = service
    profile = await dialogs.get_profile(1)
    dialog = profile.dialogs[0]

    copy = dialogs.with_mode(dialog, Mode.TEACHER)

    assert copy is not dialog
    assert copy.mode is Mode.TEACHER
    assert dialog.mode is Mode.ASSISTANT


def test_profile_timestamps_are_strings() -> None:
    now = utc_now()
    assert isinstance(now, str) and now
