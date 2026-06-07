"""Личный кабинет пользователя и прохождение симулятора."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from .database import get_db
from .security import login_required, current_user
from .forms import clean_text
from .documents import create_attempt_docx, create_attempts_xlsx

cabinet_bp = Blueprint("cabinet", __name__, url_prefix="/cabinet")


@cabinet_bp.route("/")
@login_required
def dashboard():
    user = current_user()
    db = get_db()
    attempts = db.execute("SELECT a.*, s.title AS scenario_title FROM attempts a JOIN scenarios s ON s.id=a.scenario_id WHERE a.user_id=? ORDER BY a.id DESC LIMIT 5", (user["id"],)).fetchall()
    achievements = db.execute("SELECT * FROM achievements WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return render_template("cabinet/dashboard.html", user=user, attempts=attempts, achievements=achievements, breadcrumbs=[("Главная", "/"), ("Личный кабинет", None)])


@cabinet_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        get_db().execute("UPDATE users SET full_name=?, email=? WHERE id=?", (clean_text(request.form.get("full_name"), 160), clean_text(request.form.get("email"), 160), user["id"]))
        get_db().commit()
        flash("Профиль обновлен.", "success")
        return redirect(url_for("cabinet.profile"))
    return render_template("cabinet/profile.html", user=user, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Профиль", None)])


@cabinet_bp.route("/simulator")
@login_required
def simulator():
    scenarios = get_db().execute("SELECT * FROM scenarios WHERE is_public=1 ORDER BY id").fetchall()
    return render_template("cabinet/simulator.html", scenarios=scenarios, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Симулятор", None)])


@cabinet_bp.route("/simulator/<int:scenario_id>", methods=["GET", "POST"])
@login_required
def run_scenario(scenario_id):
    user = current_user()
    db = get_db()
    scenario = db.execute("SELECT * FROM scenarios WHERE id=?", (scenario_id,)).fetchone()
    questions = db.execute("SELECT * FROM questions WHERE scenario_id=? ORDER BY sort_order", (scenario_id,)).fetchall()
    options = {q["id"]: db.execute("SELECT * FROM options WHERE question_id=?", (q["id"],)).fetchall() for q in questions}
    if request.method == "POST":
        started = datetime.now().isoformat(timespec="seconds")
        cur = db.execute("INSERT INTO attempts(user_id,scenario_id,started_at,finished_at,score,status) VALUES (?,?,?,?,?,?)", (user["id"], scenario_id, started, started, 0, "finished"))
        attempt_id = cur.lastrowid
        score = 0
        for q in questions:
            option_id = int(request.form.get(f"q_{q['id']}", "0") or 0)
            option = db.execute("SELECT * FROM options WHERE id=? AND question_id=?", (option_id, q["id"])).fetchone()
            is_correct = 1 if option and option["is_correct"] else 0
            if is_correct:
                score += q["points"]
            db.execute("INSERT INTO answers(attempt_id,question_id,option_id,is_correct,created_at) VALUES (?,?,?,?,?)", (attempt_id, q["id"], option_id, is_correct, started))
        db.execute("UPDATE attempts SET score=? WHERE id=?", (score, attempt_id))
        if score >= 25:
            db.execute("INSERT INTO achievements(user_id,title,description,awarded_at) VALUES (?,?,?,?)", (user["id"], "Успешное прохождение", f"Получено {score} баллов за сценарий {scenario['title']}", started))
        db.commit()
        flash(f"Симулятор завершен. Итоговый балл: {score}.", "success")
        return redirect(url_for("cabinet.attempt_detail", attempt_id=attempt_id))
    return render_template("cabinet/run_scenario.html", scenario=scenario, questions=questions, options=options, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Симулятор", url_for("cabinet.simulator")), (scenario["title"], None)])


@cabinet_bp.route("/attempts")
@login_required
def attempts():
    user = current_user()
    rows = get_db().execute("SELECT a.*, s.title AS scenario_title FROM attempts a JOIN scenarios s ON s.id=a.scenario_id WHERE a.user_id=? ORDER BY a.id DESC", (user["id"],)).fetchall()
    return render_template("cabinet/attempts.html", attempts=rows, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Попытки", None)])


@cabinet_bp.route("/attempt/<int:attempt_id>")
@login_required
def attempt_detail(attempt_id):
    user = current_user()
    db = get_db()
    attempt = db.execute("SELECT a.*, s.title AS scenario_title FROM attempts a JOIN scenarios s ON s.id=a.scenario_id WHERE a.id=? AND a.user_id=?", (attempt_id, user["id"])).fetchone()
    answers = db.execute("SELECT q.text, q.explanation, o.text AS option_text, ans.is_correct FROM answers ans JOIN questions q ON q.id=ans.question_id JOIN options o ON o.id=ans.option_id WHERE ans.attempt_id=?", (attempt_id,)).fetchall()
    return render_template("cabinet/attempt_detail.html", attempt=attempt, answers=answers, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Попытки", url_for("cabinet.attempts")), ("Результат", None)])


@cabinet_bp.route("/files", methods=["GET", "POST"])
@login_required
def files():
    user = current_user()
    db = get_db()
    if request.method == "POST" and "file" in request.files:
        f = request.files["file"]
        if f.filename:
            safe = secure_filename(f.filename)
            saved_name = f"{user['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}"
            path = Path(current_app.config["UPLOAD_FOLDER"]) / saved_name
            f.save(path)
            db.execute("INSERT INTO uploaded_files(user_id,original_name,saved_name,file_size,uploaded_at) VALUES (?,?,?,?,?)", (user["id"], f.filename, saved_name, path.stat().st_size, datetime.now().isoformat(timespec="seconds")))
            db.commit()
            flash("Файл загружен в файловое хранилище проекта.", "success")
    rows = db.execute("SELECT * FROM uploaded_files WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return render_template("cabinet/files.html", files=rows, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Файлы", None)])


@cabinet_bp.route("/achievements")
@login_required
def achievements():
    user = current_user()
    rows = get_db().execute("SELECT * FROM achievements WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return render_template("cabinet/achievements.html", achievements=rows, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Достижения", None)])


@cabinet_bp.route("/documents")
@login_required
def documents():
    user = current_user()
    rows = get_db().execute("SELECT * FROM generated_documents WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return render_template("cabinet/documents.html", documents=rows, breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Документы", None)])


@cabinet_bp.route("/documents/xlsx")
@login_required
def export_xlsx():
    path = create_attempts_xlsx(current_user())
    return send_file(path, as_attachment=True)


@cabinet_bp.route("/documents/docx/<int:attempt_id>")
@login_required
def export_docx(attempt_id):
    path = create_attempt_docx(current_user(), attempt_id)
    return send_file(path, as_attachment=True)


@cabinet_bp.route("/settings")
@login_required
def settings():
    return render_template("cabinet/settings.html", user=current_user(), breadcrumbs=[("Главная", "/"), ("Личный кабинет", url_for("cabinet.dashboard")), ("Настройки", None)])
