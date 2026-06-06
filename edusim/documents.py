"""Формирование документов DOCX и XLSX из приложения."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from docx import Document
from openpyxl import Workbook
from flask import current_app

from .database import get_db


def _safe_name(prefix: str, suffix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}.{suffix}"


def create_attempt_docx(user, attempt_id: int) -> Path:
    db = get_db()
    attempt = db.execute("SELECT a.*, s.title AS scenario_title FROM attempts a JOIN scenarios s ON s.id=a.scenario_id WHERE a.id=?", (attempt_id,)).fetchone()
    answers = db.execute("""SELECT q.text AS question, o.text AS option_text, ans.is_correct
                            FROM answers ans
                            JOIN questions q ON q.id=ans.question_id
                            JOIN options o ON o.id=ans.option_id
                            WHERE ans.attempt_id=?""", (attempt_id,)).fetchall()
    doc = Document()
    doc.add_heading("Отчет о прохождении образовательного симулятора", 0)
    doc.add_paragraph(f"Пользователь: {user['full_name']}")
    doc.add_paragraph(f"Сценарий: {attempt['scenario_title']}")
    doc.add_paragraph(f"Балл: {attempt['score']}")
    doc.add_paragraph(f"Статус: {attempt['status']}")
    table = doc.add_table(rows=1, cols=3)
    headers = table.rows[0].cells
    headers[0].text = "Вопрос"
    headers[1].text = "Выбранный ответ"
    headers[2].text = "Результат"
    for ans in answers:
        row = table.add_row().cells
        row[0].text = ans["question"]
        row[1].text = ans["option_text"]
        row[2].text = "Верно" if ans["is_correct"] else "Ошибка"
    path = Path(current_app.config["GENERATED_FOLDER"]) / _safe_name("attempt_report", "docx")
    doc.save(path)
    db.execute("INSERT INTO generated_documents(user_id, doc_type, title, file_path, created_at) VALUES (?,?,?,?,?)",
               (user["id"], "docx", "Отчет о прохождении", str(path), datetime.now().isoformat(timespec="seconds")))
    db.commit()
    return path


def create_attempts_xlsx(user) -> Path:
    db = get_db()
    rows = db.execute("""SELECT a.id, s.title, a.started_at, a.finished_at, a.score, a.status
                         FROM attempts a JOIN scenarios s ON s.id=a.scenario_id
                         WHERE a.user_id=? ORDER BY a.id DESC""", (user["id"],)).fetchall()
    wb = Workbook()
    ws = wb.active
    ws.title = "Результаты"
    ws.append(["ID", "Сценарий", "Начало", "Завершение", "Балл", "Статус"])
    for row in rows:
        ws.append([row["id"], row["title"], row["started_at"], row["finished_at"], row["score"], row["status"]])
    path = Path(current_app.config["GENERATED_FOLDER"]) / _safe_name("attempts_export", "xlsx")
    wb.save(path)
    db.execute("INSERT INTO generated_documents(user_id, doc_type, title, file_path, created_at) VALUES (?,?,?,?,?)",
               (user["id"], "xlsx", "Выгрузка результатов", str(path), datetime.now().isoformat(timespec="seconds")))
    db.commit()
    return path
