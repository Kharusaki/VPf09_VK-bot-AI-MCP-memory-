"""Тесты атомарного JSON-хранилища."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storage.server.json_store import JsonUserStore


@pytest.fixture()
def store(tmp_path: Path) -> JsonUserStore:
    store = JsonUserStore(tmp_path / "users", max_file_bytes=10_000)
    store.ensure_ready()
    return store


async def test_write_read_round_trip(store: JsonUserStore) -> None:
    data = {"user_id": 42, "display_name": "Иван", "dialogs": []}

    await store.write(42, data)

    assert await store.read(42) == data
    assert (store.data_dir / "42.json").exists()


async def test_read_missing_user_returns_none(store: JsonUserStore) -> None:
    assert await store.read(999) is None


async def test_delete_user(store: JsonUserStore) -> None:
    await store.write(1, {"user_id": 1})

    assert await store.delete(1) is True
    assert await store.delete(1) is False
    assert await store.read(1) is None


async def test_list_users_sorted_and_ignores_service_files(store: JsonUserStore) -> None:
    await store.write(30, {"user_id": 30})
    await store.write(5, {"user_id": 5})
    await store.write(100, {"user_id": 100})
    (store.data_dir / "not-a-user.json").write_text("{}", encoding="utf-8")
    (store.data_dir / ".hidden.json").write_text("{}", encoding="utf-8")

    assert await store.list_users() == [5, 30, 100]


async def test_stats_counts_files_and_bytes(store: JsonUserStore) -> None:
    await store.write(1, {"user_id": 1})
    await store.write(2, {"user_id": 2})

    stats = await store.stats()

    assert stats["users"] == 2
    assert stats["total_bytes"] > 0
    assert stats["data_dir"] == str(store.data_dir)


async def test_corrupt_json_is_backed_up_and_reset(store: JsonUserStore) -> None:
    path = store.data_dir / "7.json"
    path.write_text("{not valid json", encoding="utf-8")

    assert await store.read(7) is None
    assert not path.exists()
    backups = list(store.data_dir.glob("7.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not valid json"


async def test_non_object_json_is_treated_as_corrupt(store: JsonUserStore) -> None:
    path = store.data_dir / "8.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    assert await store.read(8) is None
    assert list(store.data_dir.glob("8.corrupt-*.json"))


async def test_oversized_file_is_not_read(store: JsonUserStore) -> None:
    path = store.data_dir / "9.json"
    path.write_text(json.dumps({"text": "a" * 20_000}), encoding="utf-8")

    assert await store.read(9) is None
    assert list(store.data_dir.glob("9.corrupt-*.json"))


async def test_write_rejects_oversized_profile(store: JsonUserStore) -> None:
    with pytest.raises(ValueError, match="превышает лимит"):
        await store.write(10, {"text": "a" * 20_000})


async def test_concurrent_writes_leave_valid_json(store: JsonUserStore) -> None:
    import asyncio

    async def write(index: int) -> None:
        await store.write(11, {"user_id": 11, "index": index})

    await asyncio.gather(*(write(index) for index in range(20)))

    data = await store.read(11)
    assert data is not None
    assert data["user_id"] == 11
    assert 0 <= data["index"] < 20
    assert not list(store.data_dir.glob("*.tmp"))
