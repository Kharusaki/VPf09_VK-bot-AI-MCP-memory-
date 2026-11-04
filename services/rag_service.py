"""RAG-контейнер: загрузка файлов, чанкинг, эмбеддинги, поиск.

Менеджер загружает файлы (txt, md, pdf) в контейнер, бот векторизует их
и отвечает по содержимому в режиме «Менеджер по базе знаний».
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.settings import Settings
from utils.errors import StorageError

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
TOP_K = 5
EMBEDDING_DIM = 1536  # openai/text-embedding-3-small


@dataclass
class Chunk:
    """Один чанк документа с эмбеддингом."""

    text: str
    source: str  # путь к файлу
    index: int
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "index": self.index,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        return cls(
            text=str(data.get("text", "")),
            source=str(data.get("source", "")),
            index=int(data.get("index", 0)),
            embedding=[float(v) for v in data.get("embedding", [])],
        )


class RAGService:
    """Загрузка файлов, чанкинг, эмбеддинги и семантический поиск."""

    def __init__(self, settings: Settings, rag_dir: Path | None = None) -> None:
        self.settings = settings
        self.rag_dir = rag_dir or settings.data_dir / "rag"
        self.rag_dir.mkdir(parents=True, exist_ok=True)
        self.chunks: list[Chunk] = []
        self._loaded = False

    # --- Загрузка файлов ---

    def load_file(self, path: str | Path) -> int:
        """Прочитать файл, разбить на чанки. Возвращает число чанков."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

        text = self._read_file(path)
        if not text.strip():
            logger.warning("Файл пустой: %s", path)
            return 0

        new_chunks = self._chunk(text, str(path))
        len(self.chunks)
        self.chunks.extend(new_chunks)

        logger.info("Загружено %d чанков из %s (всего: %d)", len(new_chunks), path, len(self.chunks))
        return len(new_chunks)

    def load_files(self, paths: list[str | Path]) -> int:
        """Загрузить несколько файлов. Возвращает общее число чанков."""
        total = 0
        for p in paths:
            total += self.load_file(p)
        return total

    @staticmethod
    def _read_file(path: Path) -> str:
        """Прочитать текст из файла. Поддерживает .txt, .md, .pdf."""
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".log"}:
            return path.read_text(encoding="utf-8", errors="replace")
        if suffix == ".pdf":
            return _read_pdf(path)
        # По умолчанию читаем как текст
        return path.read_text(encoding="utf-8", errors="replace")

    # --- Чанкинг ---

    def _chunk(self, text: str, source: str) -> list[Chunk]:
        """Разбить текст на перекрывающиеся чанки."""
        words = text.split()
        if not words:
            return []

        chunks: list[Chunk] = []
        chunk_size = CHUNK_SIZE
        overlap = CHUNK_OVERLAP

        start = 0
        idx = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(Chunk(text=chunk_text, source=source, index=idx))
            idx += 1
            start = end - overlap if end < len(words) else end

        return chunks

    # --- Эмбеддинги ---

    async def embed_all(self) -> int:
        """Сгенерировать эмбеддинги для всех чанков без эмбеддингов."""
        missing = [c for c in self.chunks if not c.embedding]
        if not missing:
            return 0

        # Группируем по 100 чанков (лимит OpenAI embeddings API)
        batch_size = 100
        total = 0
        for i in range(0, len(missing), batch_size):
            batch = missing[i : i + batch_size]
            texts = [c.text for c in batch]
            embeddings = await self._embed_texts(texts)
            for chunk, emb in zip(batch, embeddings, strict=False):
                chunk.embedding = emb
                total += 1

        logger.info("Сгенерировано %d эмбеддингов", total)
        return total

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Послать тексты в эмбеддинговую модель ProxyAPI."""
        from openai import AsyncOpenAI

        base_url = self.settings.proxy_base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"

        client = AsyncOpenAI(
            api_key=self.settings.proxy_api_key,
            base_url=base_url,
            timeout=max(5.0, self.settings.request_timeout),
            max_retries=0,
        )

        try:
            response = await client.embeddings.create(
                model=self.settings.embedding_model,
                input=texts,
            )
        except Exception as exc:
            logger.warning("Эмбеддинги (%s): %s", self.settings.embedding_model, exc)
            raise StorageError(f"Не удалось создать эмбеддинги: {exc}") from exc

        return [d.embedding for d in response.data]

    # --- Сохранение / загрузка ---

    def save(self) -> None:
        """Сохранить все чанки в JSON."""
        path = self.rag_dir / "chunks.json"
        tmp = path.with_suffix(".tmp")
        data = [c.to_dict() for c in self.chunks]
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        self._loaded = True
        logger.info("RAG-контейнер сохранён: %d чанков", len(self.chunks))

    def load(self) -> int:
        """Загрузить чанки из JSON. Возвращает число чанков."""
        path = self.rag_dir / "chunks.json"
        if not path.exists():
            self._loaded = False
            return 0

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.chunks = [Chunk.from_dict(item) for item in data if isinstance(item, dict)]
            self._loaded = True
            logger.info("RAG-контейнер загружен: %d чанков", len(self.chunks))
            return len(self.chunks)
        except Exception as exc:
            logger.warning("RAG-контейнер повреждён (%s), очищаю: %s", path, exc)
            path.rename(path.with_suffix(".corrupt"))
            self.chunks = []
            self._loaded = False
            return 0

    # --- Поиск ---

    async def search(self, query: str, top_k: int | None = None) -> list[Chunk]:
        """Найти топ-K чанков по смыслу запроса."""
        if not self.chunks:
            return []

        k = top_k or TOP_K
        query_emb = await self._embed_texts([query])
        query_vec = query_emb[0]

        scored: list[tuple[float, Chunk]] = []
        for chunk in self.chunks:
            if not chunk.embedding:
                continue
            sim = cosine_similarity(query_vec, chunk.embedding)
            scored.append((sim, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:k]]

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    def clear(self) -> None:
        """Очистить контейнер."""
        self.chunks = []
        self._loaded = False
        path = self.rag_dir / "chunks.json"
        if path.exists():
            path.unlink()
        logger.info("RAG-контейнер очищен")


def _read_pdf(path: Path) -> str:
    """Простое извлечение текста из PDF (без внешних зависимостей)."""
    try:
        import PyPDF2
    except ImportError as err:
        raise StorageError(
            "Для чтения PDF установите PyPDF2: pip install PyPDF2"
        ) from err

    text_parts: list[str] = []
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as exc:
        raise StorageError(f"Не удалось прочитать PDF {path}: {exc}") from exc

    return "\n\n".join(text_parts)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Косинусное сходство двух векторов."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)