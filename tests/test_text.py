"""Тесты работы с текстом и лимитами VK."""

from __future__ import annotations

from utils.text import (
    clean_text,
    normalize_title,
    split_text,
    truncate_utf16,
    utf16_len,
)


def test_utf16_len_counts_emoji_as_two_units() -> None:
    assert utf16_len("привет") == 6
    assert utf16_len("🙂") == 2
    assert utf16_len("а🙂б") == 4


def test_clean_text_normalizes_spaces_and_newlines() -> None:
    assert clean_text("  привет \t мир  ") == "привет мир"
    assert clean_text("a\r\nb\r\n\r\n\r\nc") == "a\nb\n\nc"
    assert clean_text(None) == ""
    assert clean_text("a\x00b") == "ab"


def test_truncate_utf16_does_not_split_emoji() -> None:
    assert truncate_utf16("ab🙂cd", 4) == "ab🙂"
    assert truncate_utf16("ab🙂cd", 3) == "ab"
    assert truncate_utf16("abc", 0) == ""
    assert truncate_utf16("abc", 10) == "abc"


def test_normalize_title_collapses_spaces_and_limits() -> None:
    assert normalize_title("  Мой   диалог ") == "Мой диалог"
    assert normalize_title("x" * 80) == "x" * 50
    assert normalize_title(None) == ""


def test_split_text_short_text_is_single_chunk() -> None:
    assert split_text("короткий ответ", 100) == ["короткий ответ"]
    assert split_text("   ", 100) == []


def test_split_text_respects_utf16_limit() -> None:
    text = ("Предложение номер один. " * 200).strip()
    chunks = split_text(text, 300)

    assert len(chunks) > 1
    assert all(utf16_len(chunk) <= 300 for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks)
    assert "".join(chunk.replace(" ", "") for chunk in chunks) == text.replace(" ", "")


def test_split_text_handles_text_without_spaces() -> None:
    chunks = split_text("a" * 250, 100)

    assert len(chunks) == 3
    assert all(utf16_len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks) == "a" * 250


def test_split_text_prefers_paragraph_breaks() -> None:
    text = "Первый абзац.\n" + "Второй абзац. " * 40
    chunks = split_text(text, 120)

    assert len(chunks) >= 2
    assert chunks[0].endswith("Первый абзац.") or chunks[0].endswith("Второй абзац.")
