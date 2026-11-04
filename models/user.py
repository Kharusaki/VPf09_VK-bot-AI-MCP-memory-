"""Модель профиля пользователя."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from utils.time import utc_now

from .dialog import Dialog


@dataclass(slots=True)
class UserProfile:
    """Профиль пользователя: настройки и список диалогов."""

    user_id: int
    display_name: str
    created_at: str
    updated_at: str
    active_dialog_id: str
    dialog_counter: int
    dialogs: list[Dialog] = field(default_factory=list)

    @property
    def active_dialog(self) -> Dialog | None:
        """Активный диалог или первый доступный."""
        for dialog in self.dialogs:
            if dialog.id == self.active_dialog_id:
                return dialog
        return self.dialogs[0] if self.dialogs else None

    def find_dialog(self, dialog_id: str) -> Dialog | None:
        return next((dialog for dialog in self.dialogs if dialog.id == dialog_id), None)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UserProfile:
        raw_dialogs = data.get("dialogs")
        dialogs: list[Dialog] = []
        if isinstance(raw_dialogs, list):
            dialogs = [
                Dialog.from_dict(item)
                for item in raw_dialogs
                if isinstance(item, Mapping)
            ]

        settings = data.get("settings")
        settings = settings if isinstance(settings, Mapping) else {}
        active_id = str(
            settings.get("active_dialog_id") or (dialogs[0].id if dialogs else "")
        )
        counter = settings.get("dialog_counter") or len(dialogs) or 1

        return cls(
            user_id=int(data.get("user_id") or 0),
            display_name=str(data.get("display_name") or ""),
            created_at=str(data.get("created_at") or "") or utc_now(),
            updated_at=str(data.get("updated_at") or "") or utc_now(),
            active_dialog_id=active_id,
            dialog_counter=int(counter),
            dialogs=dialogs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": {
                "active_dialog_id": self.active_dialog_id,
                "dialog_counter": self.dialog_counter,
            },
            "dialogs": [dialog.to_dict() for dialog in self.dialogs],
        }
