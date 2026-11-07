"""Интеграционный тест: настоящий MCP-сервер и настоящий клиент.

Проверяется транспорт Streamable HTTP, регистрация инструментов и полный
цикл сохранения профиля в JSON. VK и LLM здесь не участвуют.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from models.dialog import Dialog
from models.enums import MessageRole, Mode
from models.message import ChatMessage
from models.user import UserProfile
from storage.client.mcp_client import MCPStorageClient
from storage.client.repository import StorageRepository
from utils.time import utc_now

ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(process: subprocess.Popen[bytes], host: str, port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("MCP-сервер завершился при запуске")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise AssertionError("MCP-сервер не открыл порт за 20 секунд")


@pytest.fixture()
def server(tmp_path: Path):
    port = _free_port()
    data_dir = tmp_path / "users"
    env = os.environ.copy()
    env.update(
        {
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(port),
            "MCP_PATH": "/mcp",
            "DATA_DIR": str(data_dir),
            "QUESTIONNAIRE_DIR": str(tmp_path / "questionnaires"),
            "LOG_LEVEL": "WARNING",
            "PYTHONUNBUFFERED": "1",
        }
    )

    process = subprocess.Popen(
        [sys.executable, "-m", "storage.server"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(process, "127.0.0.1", port)
        yield f"http://127.0.0.1:{port}/mcp", data_dir, process
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def _profile() -> UserProfile:
    now = utc_now()
    dialog = Dialog(
        id="dialog-1",
        title="Тестовый диалог",
        mode=Mode.PROGRAMMER,
        created_at=now,
        updated_at=now,
        messages=[
            ChatMessage(role=MessageRole.USER, content="Привет", timestamp=now),
            ChatMessage(role=MessageRole.ASSISTANT, content="Здравствуйте", timestamp=now),
        ],
    )
    return UserProfile(
        user_id=777,
        display_name="Тестовый пользователь",
        created_at=now,
        updated_at=now,
        active_dialog_id=dialog.id,
        dialog_counter=2,
        dialogs=[dialog],
    )


async def test_mcp_storage_end_to_end(server) -> None:
    url, data_dir, _process = server
    client = MCPStorageClient(url, timeout=10, connect_timeout=10)
    repository = StorageRepository(client)

    await client.start()
    try:
        ping = await repository.ping()
        assert ping["ok"] is True
        assert ping["service"] == "vk-assistant-storage"

        assert await repository.load_user(777) is None
        assert await repository.list_user_ids() == []

        profile = _profile()
        await repository.save_user(profile)

        assert (data_dir / "777.json").exists()
        loaded = await repository.load_user(777)
        assert loaded is not None
        assert loaded.user_id == 777
        assert loaded.display_name == "Тестовый пользователь"
        assert loaded.active_dialog_id == "dialog-1"
        assert loaded.dialog_counter == 2
        assert loaded.active_dialog is not None
        assert loaded.active_dialog.title == "Тестовый диалог"
        assert loaded.active_dialog.mode is Mode.PROGRAMMER
        assert [message.content for message in loaded.active_dialog.messages] == [
            "Привет",
            "Здравствуйте",
        ]

        assert await repository.list_user_ids() == [777]

        stats = await repository.stats()
        assert stats["ok"] is True
        assert stats["users"] == 1

        saved = await repository.save_questionnaire(
            user_id=777,
            dialog_id="dialog-1",
            dialog_title="Анкета",
            display_name="Тестовый пользователь",
            profile={"student_name": "Артём Соколов", "current_level": "A2"},
        )
        assert saved["ok"] is True
        questionnaire_path = Path(saved["path"])
        assert questionnaire_path.exists()
        questionnaire = json.loads(questionnaire_path.read_text(encoding="utf-8"))
        assert questionnaire["student_name"] == "Артём Соколов"
        assert questionnaire["current_level"] == "A2"
        assert questionnaire["contact_info"] == "не указано"
        assert questionnaire["user_id"] == 777
        assert questionnaire["dialog_title"] == "Анкета"

        await repository.delete_user(777)
        assert await repository.load_user(777) is None
        assert await repository.list_user_ids() == []
        assert not (data_dir / "777.json").exists()
    finally:
        await client.stop()


async def test_mcp_client_can_restart_session(server) -> None:
    url, _data_dir, process = server
    client = MCPStorageClient(url, timeout=10, connect_timeout=10, retry_delay=0.2)

    await client.start()
    try:
        assert (await client.ping())["ok"] is True
    finally:
        await client.stop()

    await client.start()
    try:
        assert (await client.ping())["ok"] is True
    finally:
        await client.stop()

    assert process.poll() is None
