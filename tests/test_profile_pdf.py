"""Тесты HTML-шаблона и генерации PDF-анкеты."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from models.questionnaire import normalize_profile
from services.profile_pdf import generate_profile_pdf, render_profile_html

SAMPLE = {
    "student_name": "Артём Соколов",
    "age_or_grade": "11 лет, 5 класс",
    "current_level": "A2",
    "learning_goal": "Разговорный английский",
    "preferred_schedule": "Пн и ср в 16:00",
    "format_preference": "Офлайн, группа",
    "previous_experience": "Школьная программа",
    "special_notes": "Застенчивый",
    "contact_info": "Папа Дмитрий, +7 912 555-11-22",
    "next_steps": "Пробный урок 18 ноября",
    "source_file": "anketa_1_dialog.json",
    "user_id": 100128592,
    "dialog_title": "Анкета Артёма",
}


def test_render_profile_html_contains_fields_and_is_escaped() -> None:
    html = render_profile_html({**SAMPLE, "special_notes": "<script>alert(1)</script>"})

    assert "Анкета ученика" in html
    assert "Артём Соколов" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_render_profile_html_uses_defaults() -> None:
    html = render_profile_html({"student_name": "Мария"})

    assert normalize_profile({})["contact_info"] in html


def test_generate_profile_pdf_creates_readable_pdf(tmp_path: Path) -> None:
    pdf_path = generate_profile_pdf(SAMPLE, output_dir=tmp_path)

    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.read_bytes().startswith(b"%PDF")

    text = PdfReader(str(pdf_path)).pages[0].extract_text()
    assert "Артём Соколов" in text
    assert "Разговорный английский" in text
