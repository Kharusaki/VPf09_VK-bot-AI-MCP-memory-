"""Запуск всего стека одной командой: python run_all.py.

Скрипт поднимает MCP-сервер отдельным процессом, ждёт открытия порта и
запускает VK-бота. При выходе сервер останавливается. Если сервер уже
запущен вручную, используется он.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _port_open(host: str, port: int) -> bool:
    """Проверить, принимает ли кто-то TCP-соединения на порту."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _stop_process(process: subprocess.Popen[bytes] | None) -> None:
    """Корректно остановить дочерний сервер."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    """Поднять MCP-сервер и запустить бота."""
    from bot.main import run_bot
    from config.settings import load_settings
    from storage.server.config import load_server_settings
    from utils.logging import configure_logging

    settings = load_settings()
    configure_logging(settings.log_level, settings.log_file)
    server_settings = load_server_settings()
    client_host = (
        "127.0.0.1"
        if server_settings.host in {"0.0.0.0", "::"}
        else server_settings.host
    )

    server_process: subprocess.Popen[bytes] | None = None
    if _port_open(client_host, server_settings.port):
        print(f"MCP-сервер уже запущен: {server_settings.url}")
    else:
        server_process = subprocess.Popen(
            [sys.executable, "-m", "storage.server"],
            cwd=str(BASE_DIR),
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if server_process.poll() is not None:
                raise SystemExit(
                    "MCP-сервер завершился при запуске. Смотрите ошибки выше."
                )
            if _port_open(client_host, server_settings.port):
                break
            time.sleep(0.25)
        else:
            _stop_process(server_process)
            raise SystemExit("MCP-сервер не открыл порт за 20 секунд.")
        print(f"MCP-сервер запущен: {server_settings.url}")

    try:
        asyncio.run(run_bot(settings))
    except KeyboardInterrupt:
        pass
    finally:
        _stop_process(server_process)


if __name__ == "__main__":
    main()
