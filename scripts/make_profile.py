"""Создание PDF-анкет из JSON бота, JSON с диалогом или TXT.

Примеры:
    python scripts/make_profile.py
    python scripts/make_profile.py data/questionnaires/anketa_123_abc.json
    python scripts/make_profile.py input/dialog.txt
    python scripts/make_profile.py --list
    python scripts/make_profile.py --input-dir C:/ankety --out C:/reports
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import load_settings  # noqa: E402
from services.ai_service import AIService  # noqa: E402
from services.profile_pdf import DEFAULT_REPORTS_DIR, generate_profile_pdf  # noqa: E402
from services.questionnaire_extract import (  # noqa: E402
    extract_profile_with_ai,
    load_source,
)
from utils.errors import AppError, ConfigError  # noqa: E402

DEFAULT_INPUT_DIR = BASE_DIR / "data" / "questionnaires"
_META_KEYS = (
    "user_id",
    "display_name",
    "dialog_id",
    "dialog_title",
    "created_at",
    "updated_at",
    "student_name",
)


def _input_dir() -> Path:
    raw = os.getenv("QUESTIONNAIRE_DIR", "").strip()
    if not raw:
        return DEFAULT_INPUT_DIR
    path = Path(raw).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


def _read_metadata(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, Mapping):
        return {}
    return {key: data[key] for key in _META_KEYS if data.get(key) not in (None, "")}


def _collect_files(explicit: list[str], input_dir: Path) -> list[Path]:
    if explicit:
        result: list[Path] = []
        for raw in explicit:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = BASE_DIR / path
            result.append(path.resolve())
        return result

    if not input_dir.exists():
        return []
    return sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".json"
    )


def _list_files(files: list[Path]) -> None:
    if not files:
        print("Анкет не найдено.")
        return
    print(f"Анкет в очереди: {len(files)}")
    for path in files:
        meta = _read_metadata(path)
        name = meta.get("student_name") or "—"
        updated = meta.get("updated_at") or "—"
        print(f"  {path.name}\n    ученик: {name}\n    обновлено: {updated}")


async def _generate(
    path: Path,
    out_dir: Path | None,
    allow_ai: bool,
    ai: AIService | None,
) -> tuple[Path | None, bool]:
    if not path.exists() or not path.is_file():
        print(f"[ERROR] Файл не найден: {path}")
        return None, True

    text, profile = load_source(path)
    needs_ai = profile is None

    if needs_ai and not allow_ai:
        print(f"[SKIP] {path.name}: это не готовая анкета, AI отключён (--no-ai).")
        return None, False
    if needs_ai and ai is None:
        raise ConfigError(
            "Для извлечения анкеты из диалога нужен PROXY_API_KEY и AI_PROVIDER в .env."
        )

    if profile is None and ai is not None:
        print(f"[AI] Извлекаю анкету из {path.name}…")
        profile = await extract_profile_with_ai(text, ai)

    data: dict[str, Any] = dict(profile or {})
    data.update(_read_metadata(path))
    data["source_file"] = path.name

    pdf_path = generate_profile_pdf(data, output_dir=out_dir)
    print(f"[OK] {pdf_path}")
    return pdf_path, False


async def run(args: argparse.Namespace) -> int:
    input_dir = (
        Path(args.input_dir).expanduser()
        if args.input_dir
        else _input_dir()
    )
    if not input_dir.is_absolute():
        input_dir = BASE_DIR / input_dir
    files = _collect_files(args.files, input_dir)
    if args.list:
        _list_files(files)
        return 0

    if not files:
        print(
            "Нечего обрабатывать. Проверьте каталог "
            f"{input_dir} или передайте файл явно."
        )
        return 1

    ai: AIService | None = None
    if not args.no_ai:
        try:
            ai = AIService(load_settings())
        except ConfigError as exc:
            print(f"[WARN] AI недоступен: {exc}")
            ai = None

    out_dir = Path(args.out).expanduser().resolve() if args.out else None
    if out_dir is None:
        out_dir = DEFAULT_REPORTS_DIR

    success, failed = 0, 0
    for path in files:
        try:
            pdf_path, failed_flag = await _generate(
                path, out_dir, not args.no_ai, ai
            )
        except AppError as exc:
            print(f"[ERROR] {path.name}: {exc}")
            failed += 1
            continue
        except Exception as exc:
            print(f"[ERROR] {path.name}: {exc}")
            failed += 1
            continue
        if failed_flag:
            failed += 1
        elif pdf_path is not None:
            success += 1

    print(f"\nГотово. PDF: {success}, ошибок: {failed}")
    print(f"Каталог отчётов: {out_dir}")
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сгенерировать PDF-анкеты из JSON бота, JSON-диалогов или TXT."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Один или несколько файлов. Без аргументов — все JSON из каталога анкет.",
    )
    parser.add_argument(
        "--input-dir",
        help="Каталог с JSON-анкетами (по умолчанию data/questionnaires).",
    )
    parser.add_argument(
        "--out",
        help="Каталог для PDF (по умолчанию reports/).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Только показать список найденных анкет.",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Не вызывать AI: обрабатывать только готовые JSON-анкеты.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
