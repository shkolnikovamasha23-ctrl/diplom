"""Фабрика Flask-приложения образовательного симулятора.

Проект выполнен как сетевой ресурс: есть публичные страницы, авторизация,
личный кабинет, административная панель, работа с базой данных и файлами.
"""
from __future__ import annotations

import os
from pathlib import Path
from flask import Flask, g, request

from .database import close_db, init_db, seed_demo_data
from .routes_public import public_bp
from .routes_auth import auth_bp
from .routes_cabinet import cabinet_bp
from .routes_admin import admin_bp


def create_app() -> Flask:
    """Создать и настроить экземпляр Flask-приложения."""
    base_dir = Path(__file__).resolve().parent
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    app.config["DATABASE_PATH"] = os.environ.get("DATABASE_PATH", str(base_dir / "data" / "edusim.db"))
    app.config["UPLOAD_FOLDER"] = str(base_dir / "static" / "uploads")
    app.config["GENERATED_FOLDER"] = str(base_dir / "generated")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["GENERATED_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db()
        seed_demo_data()

    app.teardown_appcontext(close_db)
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cabinet_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        return {
            "author_name": "Нилова Мария Олеговна",
            "project_title": "EduSim — образовательный симулятор",
            "current_path": request.path,
        }

    @app.errorhandler(404)
    def page_not_found(error):
        return app.jinja_env.get_template("errors/404.html").render(error=error), 404

    @app.errorhandler(403)
    def forbidden(error):
        return app.jinja_env.get_template("errors/403.html").render(error=error), 403

    return app
