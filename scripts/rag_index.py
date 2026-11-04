"""Индексация базы знаний для режима «Менеджер по базе знаний».

Менеджер кладёт файлы в каталог data/rag/sources (или указывает путь сам), затем прогоняет этот скрипт: файлы резаются на чанки, векторизуются через ProxyAPI и сохраняются в data/rag/chunks.json. Бот подхватывает файл перезапуском или кнопкой «📚 База знаний».

Примеры:
    python scripts/rag_index.py                      # индексировать data/rag/sources
    python scripts/rag_index.py --add C:/docs/price.txt
    python scripts/rag_index.py --add C:/docs/a.md C:/docs/b.pdf
    python scripts/rag_index.py --status             # что сейчас в базе
    python scripts/rag_index.py --clear              # очистить базу
    python scripts/rag_index.py --find "сколько стоит доставка"
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import load_settings  # noqa: E402
from services.rag_service import RAGService  # noqa: E402
from utils.errors import ConfigError, StorageError  # noqa: E402
from utils.logging import configure_logging  # noqa: E402

SUPPORTED = {".txt", ".md", ".csv", ".log", ".pdf"}


def _collect_sources(sources_dir: Path) -> list[Path]:
    """Собрать поддерживаемые файлы из каталога-контейнера."""
    if not sources_dir.exists():
        return []
    return sorted(
        path
        for path in sources_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED
    )


def _copy_into_container(paths: list[Path], sources_dir: Path) -> list[Path]:
    """Скопировать переданные файлы в контейнер, чтобы они не потерялись."""
    sources_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for path in paths:
        path = path.expanduser().resolve()
        if not path.exists():
            print(f"⚠️  Пропускаю (не найден): {path}")
            continue
        if path.suffix.lower() not in SUPPORTED:
            print(f"⚠️  Пропускаю (неподдерживаемый формат): {path}")
            continue
        target = sources_dir / path.name
        if path != target:
            shutil.copy2(path, target)
        copied.append(target)
        print(f"📄 В контейнер: {target.name}")
    return copied


async def _index(rag: RAGService, files: list[Path]) -> int:
    """Загрузить файлы, создать эмбеддинги и сохранить контейнер."""
    if not files:
        print("Файлов для индексации нет.")
        return 0

    rag.clear()
    total = rag.load_files(files)
    if total == 0:
        print("Не удалось извлечь текст ни из одного файла.")
        return 0

    print(f"Нарезано чанков: {total}. Векторизую через {rag.settings.embedding_model}…")
    embedded = await rag.embed_all()
    rag.save()
    print(f"Готово: {embedded} эмбеддингов сохранено в {rag.rag_dir / 'chunks.json'}")
    return embedded


async def _find(rag: RAGService, query: str) -> None:
    if not rag.chunk_count:
        print("База знаний пуста. Сначала прогоните индексацию.")
        return

    found = await rag.search(query, top_k=rag.settings.rag_top_k)
    if not found:
        print("Ничего не найдено.")
        return

    print(f"Топ-{len(found)} фрагментов на запрос «{query}»:\n")
    for rank, chunk in enumerate(found, start=1):
        preview = chunk.text[:300].replace("\n", " ")
        print(f"{rank}. [{chunk.source}] {preview}…\n")


def _status(rag: RAGService, sources_dir: Path) -> None:
    count = rag.load()
    print(f"Файлов в контейнере: {len(_collect_sources(sources_dir))} ({sources_dir})")
    print(f"Чанков в индексе:    {count}")
    if count:
        sources = {chunk.source for chunk in rag.chunks}
        print("Источники:")
        for source in sorted(sources):
            print(f"  • {source}")
    else:
        print("Индекс пуст — прогоните: python scripts/rag_index.py")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Индексация базы знаний")
    parser.add_argument("--add", nargs="+", type=Path, help="файлы для загрузки в контейнер")
    parser.add_argument("--find", type=str, help="тестовый поиск по базе")
    parser.add_argument("--status", action="store_true", help="показать состояние базы")
    parser.add_argument("--clear", action="store_true", help="очистить индекс")
    parser.add_argument(
        "--sources",
        type=Path,
        default=None,
        help="каталог-контейнер (по умолчанию data/rag/sources)",
    )
    args = parser.parse_args()

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}")
        return 1

    configure_logging(settings.log_level, settings.log_file)
    rag = RAGService(settings)
    sources_dir = args.sources or (rag.rag_dir / "sources")

    if args.clear:
        rag.clear()
        print("Индекс очищен.")
        return 0

    if args.status:
        _status(rag, sources_dir)
        return 0

    try:
        if args.add:
            _copy_into_container(args.add, sources_dir)
            await _index(rag, _collect_sources(sources_dir))
        elif args.find:
            rag.load()
            await _find(rag, args.find)
        else:
            await _index(rag, _collect_sources(sources_dir))
    except StorageError as exc:
        print(f"Ошибка: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))