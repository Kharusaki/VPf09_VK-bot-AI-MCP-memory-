"""Операции с профилем и диалогами пользователя.

Сервис отвечает за инварианты: у пользователя всегда есть хотя бы один
диалог, активный диалог существует, название не длиннее 50 символов, а
количество диалогов не превышает лимит.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import replace

from config.settings import Settings
from models.dialog import Dialog
from models.enums import Mode
from models.user import UserProfile
from storage.client.repository import StorageRepository
from utils.errors import DialogLimitError, DialogNotFoundError, LastDialogError
from utils.text import normalize_title
from utils.time import utc_now

logger = logging.getLogger(__name__)


class DialogService:
    """Загрузка профиля и управление его диалогами."""

    def __init__(self, storage: StorageRepository, settings: Settings) -> None:
        self.storage = storage
        self.max_dialogs = settings.max_dialogs
        self.title_limit = 50

    async def get_profile(self, user_id: int, display_name: str = "") -> UserProfile:
        """Загрузить профиль, создав первый диалог при необходимости."""
        profile = await self.storage.load_user(user_id)
        changed = False

        if profile is None:
            profile = self._new_profile(user_id, display_name)
            changed = True
        elif display_name and profile.display_name != display_name:
            profile.display_name = display_name
            changed = True

        if not profile.dialogs:
            dialog = self._create_dialog(profile)
            profile.dialogs.append(dialog)
            profile.active_dialog_id = dialog.id
            changed = True

        if profile.find_dialog(profile.active_dialog_id) is None:
            profile.active_dialog_id = profile.dialogs[0].id
            changed = True

        if profile.dialog_counter < len(profile.dialogs):
            profile.dialog_counter = len(profile.dialogs)
            changed = True

        if changed:
            profile.updated_at = utc_now()
            await self.storage.save_user(profile)
        return profile

    async def save(self, profile: UserProfile) -> None:
        profile.updated_at = utc_now()
        await self.storage.save_user(profile)

    def _new_profile(self, user_id: int, display_name: str) -> UserProfile:
        now = utc_now()
        profile = UserProfile(
            user_id=user_id,
            display_name=display_name,
            created_at=now,
            updated_at=now,
            active_dialog_id="",
            dialog_counter=1,
            dialogs=[],
        )
        dialog = self._create_dialog(profile)
        profile.dialogs.append(dialog)
        profile.active_dialog_id = dialog.id
        return profile

    def _create_dialog(self, profile: UserProfile, mode: Mode | None = None) -> Dialog:
        number = max(1, profile.dialog_counter)
        profile.dialog_counter = number + 1
        now = utc_now()
        return Dialog(
            id=uuid.uuid4().hex[:12],
            title=f"Диалог {number}",
            mode=mode or Mode.ASSISTANT,
            created_at=now,
            updated_at=now,
            messages=[],
        )

    def new_dialog(self, profile: UserProfile, mode: Mode | None = None) -> Dialog:
        """Создать диалог и сделать его активным."""
        if len(profile.dialogs) >= self.max_dialogs:
            raise DialogLimitError(
                f"Достигнут лимит диалогов ({self.max_dialogs})"
            )
        dialog = self._create_dialog(profile, mode)
        profile.dialogs.append(dialog)
        profile.active_dialog_id = dialog.id
        profile.updated_at = utc_now()
        return dialog

    def switch_dialog(self, profile: UserProfile, dialog_id: str) -> Dialog:
        """Сделать диалог активным."""
        dialog = profile.find_dialog(dialog_id)
        if dialog is None:
            raise DialogNotFoundError("Диалог не найден")
        profile.active_dialog_id = dialog.id
        profile.updated_at = utc_now()
        return dialog

    def delete_dialog(self, profile: UserProfile, dialog_id: str) -> str:
        """Удалить диалог и вернуть его название."""
        if len(profile.dialogs) <= 1:
            raise LastDialogError("Нельзя удалить единственный диалог")
        dialog = profile.find_dialog(dialog_id)
        if dialog is None:
            raise DialogNotFoundError("Диалог не найден")

        profile.dialogs = [item for item in profile.dialogs if item.id != dialog_id]
        if profile.active_dialog_id == dialog_id:
            profile.active_dialog_id = profile.dialogs[0].id
        profile.updated_at = utc_now()
        return dialog.title

    def rename_dialog(self, profile: UserProfile, dialog_id: str, title: str) -> Dialog:
        """Переименовать диалог с проверкой длины."""
        dialog = profile.find_dialog(dialog_id)
        if dialog is None:
            raise DialogNotFoundError("Диалог не найден")
        normalized = normalize_title(title, self.title_limit)
        if not normalized:
            raise ValueError("Название не может быть пустым")
        dialog.title = normalized
        dialog.updated_at = utc_now()
        profile.updated_at = dialog.updated_at
        return dialog

    def clear_dialog(self, profile: UserProfile, dialog_id: str) -> Dialog:
        """Очистить историю диалога, сохранив сам диалог и режим."""
        dialog = profile.find_dialog(dialog_id)
        if dialog is None:
            raise DialogNotFoundError("Диалог не найден")
        dialog.messages.clear()
        dialog.updated_at = utc_now()
        profile.updated_at = dialog.updated_at
        return dialog

    def set_mode(self, profile: UserProfile, mode: Mode, dialog_id: str | None = None) -> Dialog:
        """Сменить режим активного или указанного диалога."""
        target_id = dialog_id or profile.active_dialog_id
        dialog = profile.find_dialog(target_id)
        if dialog is None:
            raise DialogNotFoundError("Диалог не найден")
        dialog.mode = mode
        dialog.updated_at = utc_now()
        profile.updated_at = dialog.updated_at
        return dialog

    def with_mode(self, dialog: Dialog, mode: Mode) -> Dialog:
        """Копия диалога с другим режимом (без изменения оригинала)."""
        return replace(dialog, mode=mode)
