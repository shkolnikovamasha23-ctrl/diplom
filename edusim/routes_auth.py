"""Маршруты регистрации, входа и выхода."""
from __future__ import annotations

from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db
from .forms import validate_required, validate_email, clean_text

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = clean_text(request.form.get("username"), 80)
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            get_db().execute("INSERT INTO activity_logs(user_id, action, details, created_at) VALUES (?,?,?,?)",
                             (user["id"], "login", "Пользователь вошел в систему", datetime.now().isoformat(timespec="seconds")))
            get_db().commit()
            return redirect(url_for("cabinet.dashboard"))
        flash("Неверный логин или пароль.", "danger")
    return render_template("auth/login.html", breadcrumbs=[("Главная", "/"), ("Вход", None)])


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        errors = validate_required(request.form, ["username", "full_name", "email", "password"])
        if not validate_email(request.form.get("email", "")):
            errors.append("Укажите корректный e-mail")
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            db = get_db()
            role = db.execute("SELECT id FROM roles WHERE code='student'").fetchone()
            try:
                db.execute("INSERT INTO users(username,password_hash,full_name,email,role_id,created_at,is_active) VALUES (?,?,?,?,?,?,1)",
                           (clean_text(request.form["username"], 80), generate_password_hash(request.form["password"]), clean_text(request.form["full_name"], 160), clean_text(request.form["email"], 160), role["id"], datetime.now().isoformat(timespec="seconds")))
                db.commit()
                flash("Учетная запись создана. Теперь можно войти.", "success")
                return redirect(url_for("auth.login"))
            except Exception:
                flash("Пользователь с таким логином уже существует.", "danger")
    return render_template("auth/register.html", breadcrumbs=[("Главная", "/"), ("Регистрация", None)])


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("public.index"))
