"""Простая серверная валидация форм без сторонних платных сервисов."""
from __future__ import annotations

import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_required(data: dict, fields: list[str]) -> list[str]:
    errors = []
    for field in fields:
        if not str(data.get(field, "")).strip():
            errors.append(f"Поле {field} обязательно для заполнения")
    return errors


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def clean_text(value: str, limit: int = 2000) -> str:
    value = (value or "").strip()
    return value[:limit]
