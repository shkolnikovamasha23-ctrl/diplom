"""Работа с SQLite-базой данных проекта.

База данных содержит больше десяти взаимосвязанных таблиц. Для дипломного
проекта выбран SQLite: это SQL-СУБД, файл базы хранится в репозитории и легко
проверяется без отдельного сервера. При необходимости DATABASE_PATH можно
заменить на внешний путь, подключенный томом Docker.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        role_id INTEGER NOT NULL REFERENCES roles(id),
        created_at TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        difficulty TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        summary TEXT NOT NULL,
        learning_goal TEXT NOT NULL,
        is_public INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        sort_order INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
        text TEXT NOT NULL,
        explanation TEXT NOT NULL,
        points INTEGER NOT NULL DEFAULT 10,
        sort_order INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL REFERENCES questions(id),
        text TEXT NOT NULL,
        is_correct INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
        started_at TEXT NOT NULL,
        finished_at TEXT,
        score INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'started'
    )""",
    """CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER NOT NULL REFERENCES attempts(id),
        question_id INTEGER NOT NULL REFERENCES questions(id),
        option_id INTEGER NOT NULL REFERENCES options(id),
        is_correct INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        awarded_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        topic TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'new',
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS uploaded_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        original_name TEXT NOT NULL,
        saved_name TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        uploaded_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS generated_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        doc_type TEXT NOT NULL,
        title TEXT NOT NULL,
        file_path TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        description TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        body TEXT NOT NULL,
        published_at TEXT NOT NULL
    )""",
]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = Path(current_app.config["DATABASE_PATH"])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    for statement in SCHEMA:
        db.execute(statement)
    db.commit()


def seed_demo_data() -> None:
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM roles").fetchone()[0] > 0:
        return
    now = "2026-06-05 12:00:00"
    roles = [
        ("admin", "Администратор", "Полный доступ к панели администратора и настройкам."),
        ("teacher", "Преподаватель", "Управление учебными сценариями и просмотр результатов."),
        ("student", "Студент", "Прохождение симуляторов, загрузка файлов, документы."),
    ]
    db.executemany("INSERT INTO roles(code, name, description) VALUES (?, ?, ?)", roles)
    role_map = {row["code"]: row["id"] for row in db.execute("SELECT * FROM roles").fetchall()}
    users = [
        ("admin", generate_password_hash("admin123"), "Нилова Мария Олеговна", "admin@edusim.local", role_map["admin"], now, 1),
        ("teacher", generate_password_hash("teacher123"), "Преподаватель демо", "teacher@edusim.local", role_map["teacher"], now, 1),
        ("student", generate_password_hash("student123"), "Студент демо", "student@edusim.local", role_map["student"], now, 1),
    ]
    db.executemany("INSERT INTO users(username,password_hash,full_name,email,role_id,created_at,is_active) VALUES (?,?,?,?,?,?,?)", users)
    settings = [
        ("site_name", "EduSim", "Название сетевого ресурса"),
        ("author", "Нилова Мария Олеговна", "ФИО автора ВКР"),
        ("support_email", "support@edusim.local", "Почта службы поддержки"),
        ("max_upload_mb", "8", "Максимальный размер файла"),
        ("default_language", "ru", "Язык интерфейса"),
    ]
    db.executemany("INSERT INTO settings(key,value,description) VALUES (?,?,?)", settings)
    scenario_rows = [
        ("Симулятор внедрения информационной системы", "is-implementation", "Средний", 25, "Игровой сценарий принятия управленческих решений при внедрении ИС.", "Научиться выявлять требования, риски и показатели эффективности.", 1),
        ("Симулятор реагирования на инцидент", "incident-response", "Сложный", 30, "Сценарий по анализу инцидента, коммуникации и восстановлению сервиса.", "Освоить последовательность действий при нарушении доступности сервиса.", 1),
        ("Симулятор проектного бюджета", "project-budget", "Начальный", 20, "Участник распределяет бюджет проекта между аналитикой, разработкой и тестированием.", "Понять влияние управленческих решений на сроки и качество проекта.", 1),
    ]
    db.executemany("INSERT INTO scenarios(title,slug,difficulty,duration_minutes,summary,learning_goal,is_public) VALUES (?,?,?,?,?,?,?)", scenario_rows)
    scenarios = {row["slug"]: row["id"] for row in db.execute("SELECT * FROM scenarios").fetchall()}
    module_rows = []
    for slug, scenario_id in scenarios.items():
        for i in range(1, 5):
            module_rows.append((scenario_id, f"Этап {i}: анализ решения", f"На этом этапе обучающийся изучает контекст сценария {slug}, оценивает исходные данные, выбирает действие и получает обратную связь. Материал можно использовать как контрольный пример в проектной части ВКР.", i))
    db.executemany("INSERT INTO modules(scenario_id,title,content,sort_order) VALUES (?,?,?,?)", module_rows)
    question_rows = []
    for slug, scenario_id in scenarios.items():
        question_rows.extend([
            (scenario_id, "Какое действие следует выполнить первым?", "Сначала фиксируются требования и ограничения, затем выбираются инструменты реализации.", 10, 1),
            (scenario_id, "Какой показатель лучше использовать для контроля результата?", "Для образовательного симулятора важны прогресс, баллы, завершенность и качество обратной связи.", 10, 2),
            (scenario_id, "Как снизить риск ошибок при внедрении?", "Риск снижается за счет тест-плана, ролей доступа, резервного копирования и пилотной эксплуатации.", 10, 3),
        ])
    db.executemany("INSERT INTO questions(scenario_id,text,explanation,points,sort_order) VALUES (?,?,?,?,?)", question_rows)
    option_rows = []
    for q in db.execute("SELECT id, text FROM questions").fetchall():
        option_rows.extend([
            (q["id"], "Провести анализ требований и определить критерии успеха", 1),
            (q["id"], "Сразу удалить старую систему без согласования", 0),
            (q["id"], "Игнорировать тестирование, чтобы сократить сроки", 0),
            (q["id"], "Передать все решения случайному пользователю", 0),
        ])
    db.executemany("INSERT INTO options(question_id,text,is_correct) VALUES (?,?,?)", option_rows)
    articles = [
        ("Методика обучения через симуляции", "methodology", "Симулятор помогает закрепить знания через практические ситуации, где обучающийся видит последствия каждого решения.", now),
        ("Как устроен сценарий", "scenario-design", "Каждый сценарий состоит из модулей, вопросов, вариантов действий, начисления баллов и пояснений после ответа.", now),
        ("Роли пользователей", "roles", "Администратор управляет ресурсом, преподаватель анализирует результаты, студент проходит обучение.", now),
    ]
    db.executemany("INSERT INTO articles(title,slug,body,published_at) VALUES (?,?,?,?)", articles)
    db.execute("INSERT INTO activity_logs(user_id, action, details, created_at) VALUES (NULL, 'seed', 'Созданы демонстрационные данные', ?)", (now,))
    db.commit()
