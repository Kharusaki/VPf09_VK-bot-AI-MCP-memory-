"""Генерация PDF-анкеты ученика из JSON.

Использует HTML-шаблон и xhtml2pdf (ReportLab). В отличие от WeasyPrint,
этот стек не требует установленного GTK и предсказуемо работает на Windows.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.questionnaire import PROFILE_FIELDS, normalize_profile
from utils.errors import ConfigError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
DEFAULT_TEMPLATE = "student_profile_template.html"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"

_FONT_PAIRS: tuple[tuple[str, str], ...] = (
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
    (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ),
)


def _reports_dir(output_dir: Path | None) -> Path:
    if output_dir is not None:
        return Path(output_dir).expanduser().resolve()
    raw = os.getenv("REPORT_DIR", "").strip()
    if not raw:
        return DEFAULT_REPORTS_DIR
    path = Path(raw).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _find_fonts() -> tuple[Path | None, Path | None]:
    """Найти системный шрифт с кириллицей и его жирное начертание."""
    for regular_raw, bold_raw in _FONT_PAIRS:
        regular = Path(regular_raw)
        if not regular.exists():
            continue
        bold = Path(bold_raw)
        return regular, bold if bold.exists() else None
    return None, None


def _font_css() -> tuple[str, tuple[Path, ...]]:
    regular, bold = _find_fonts()
    if regular is None:
        logger.warning("Не найден шрифт с кириллицей — PDF может отобразить текст некорректно.")
        return "", ()

    faces = [
        '@font-face { font-family: "ReportFont"; '
        f'src: url("{regular.as_uri()}"); }}'
    ]
    if bold is not None:
        faces.append(
            '@font-face { font-family: "ReportFont"; '
            f'src: url("{bold.as_uri()}"); font-weight: bold; }}'
        )
    roots = {regular.parent}
    if bold is not None:
        roots.add(bold.parent)
    return "\n".join(faces), tuple(roots)


def _profile_from(data: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = data.get("profile")
    return nested if isinstance(nested, Mapping) else data


def _safe_filename(value: str, fallback: str = "student") -> str:
    cleaned = "".join(
        char if char.isalnum() or char in "_-" else "_" for char in value
    ).strip("_")
    return (cleaned[:40] or fallback)


def render_profile_html(
    data: Mapping[str, Any],
    template_name: str = DEFAULT_TEMPLATE,
) -> str:
    """Отрендерить HTML анкеты без записи PDF (удобно для тестов)."""
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise ConfigError(f"Шаблон анкеты не найден: {template_path}")

    profile = normalize_profile(_profile_from(data))
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_name)
    font_css, _roots = _font_css()

    return template.render(
        student_name=profile["student_name"],
        rows=[(label, profile[key]) for key, label in PROFILE_FIELDS.items()],
        report_date=datetime.now().strftime("%d.%m.%Y %H:%M"),
        user_id=data.get("user_id"),
        dialog_title=data.get("dialog_title"),
        source_file=data.get("source_file") or data.get("dialog_id") or "",
        font_css=font_css,
    )


def generate_profile_pdf(
    data: Mapping[str, Any],
    output_dir: Path | None = None,
    template_name: str = DEFAULT_TEMPLATE,
) -> Path:
    """Построить PDF-анкету и вернуть путь к файлу."""
    try:
        from xhtml2pdf import pisa
        from xhtml2pdf.config.resources import ResourceAccessPolicy
    except ImportError as exc:  # pragma: no cover - зависит от окружения
        raise ConfigError(
            "Для генерации PDF установите зависимости: "
            "pip install jinja2 xhtml2pdf"
        ) from exc

    html = render_profile_html(data, template_name=template_name)
    profile = normalize_profile(_profile_from(data))

    target_dir = _reports_dir(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = _safe_filename(profile["student_name"])
    output_path = target_dir / f"anketa_{name}_{timestamp}.pdf"

    _font_css_text, font_roots = _font_css()
    policy = ResourceAccessPolicy(
        base_dir=PROJECT_ROOT,
        extra_roots=font_roots,
    )

    logger.info("Генерирую PDF анкеты: %s", output_path.name)
    with output_path.open("wb") as file:
        result = pisa.CreatePDF(
            html,
            dest=file,
            encoding="utf-8",
            resource_policy=policy,
        )
    if result.err:
        raise ValueError(f"xhtml2pdf вернул ошибку: {result.err}")

    logger.info("PDF сохранён: %s", output_path)
    return output_path


__all__ = (
    "DEFAULT_REPORTS_DIR",
    "DEFAULT_TEMPLATE",
    "TEMPLATES_DIR",
    "generate_profile_pdf",
    "render_profile_html",
)
