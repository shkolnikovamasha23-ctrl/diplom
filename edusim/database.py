import sqlite3
from pathlib import Path
from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = [
    '''CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT NOT NULL, role_id INTEGER NOT NULL REFERENCES roles(id), created_at TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1)''',
    '''CREATE TABLE IF NOT EXISTS scenarios (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, difficulty TEXT NOT NULL, duration_minutes INTEGER NOT NULL, summary TEXT NOT NULL, learning_goal TEXT NOT NULL, is_public INTEGER NOT NULL DEFAULT 1)''',
    '''CREATE TABLE IF NOT EXISTS modules (id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id INTEGER NOT NULL REFERENCES scenarios(id), title TEXT NOT NULL, content TEXT NOT NULL, sort_order INTEGER NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id INTEGER NOT NULL REFERENCES scenarios(id), text TEXT NOT NULL, explanation TEXT NOT NULL, points INTEGER NOT NULL DEFAULT 10, sort_order INTEGER NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS options (id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER NOT NULL REFERENCES questions(id), text TEXT NOT NULL, is_correct INTEGER NOT NULL DEFAULT 0)''',
    '''CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), scenario_id INTEGER NOT NULL REFERENCES scenarios(id), started_at TEXT NOT NULL, finished_at TEXT, score INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'started')''',
    '''CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER NOT NULL REFERENCES attempts(id), question_id INTEGER NOT NULL REFERENCES questions(id), option_id INTEGER NOT NULL REFERENCES options(id), is_correct INTEGER NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS scenario_steps (id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id INTEGER NOT NULL REFERENCES scenarios(id), code TEXT NOT NULL, title TEXT NOT NULL, context TEXT NOT NULL, file_required INTEGER NOT NULL DEFAULT 0, file_instruction TEXT NOT NULL DEFAULT '', sort_order INTEGER NOT NULL, UNIQUE(scenario_id, code))''',
    '''CREATE TABLE IF NOT EXISTS scenario_choices (id INTEGER PRIMARY KEY AUTOINCREMENT, step_id INTEGER NOT NULL REFERENCES scenario_steps(id), text TEXT NOT NULL, feedback TEXT NOT NULL, next_step_code TEXT, delta_time INTEGER NOT NULL DEFAULT 0, delta_budget INTEGER NOT NULL DEFAULT 0, delta_risk INTEGER NOT NULL DEFAULT 0, delta_quality INTEGER NOT NULL DEFAULT 0, delta_compliance INTEGER NOT NULL DEFAULT 0, score INTEGER NOT NULL DEFAULT 0)''',
    '''CREATE TABLE IF NOT EXISTS simulation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER NOT NULL REFERENCES attempts(id), step_id INTEGER NOT NULL REFERENCES scenario_steps(id), choice_id INTEGER NOT NULL REFERENCES scenario_choices(id), uploaded_file_id INTEGER REFERENCES uploaded_files(id), time_spent INTEGER NOT NULL, budget_spent INTEGER NOT NULL, risk_level INTEGER NOT NULL, quality INTEGER NOT NULL, compliance INTEGER NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL, description TEXT NOT NULL, awarded_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL, topic TEXT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new', created_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS uploaded_files (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), original_name TEXT NOT NULL, saved_name TEXT NOT NULL, file_size INTEGER NOT NULL, uploaded_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS generated_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), doc_type TEXT NOT NULL, title TEXT NOT NULL, file_path TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE NOT NULL, value TEXT NOT NULL, description TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS activity_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id), action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, body TEXT NOT NULL, published_at TEXT NOT NULL)'''
]

ATTEMPT_COLUMNS = {
    'time_spent': 'INTEGER NOT NULL DEFAULT 0',
    'budget_spent': 'INTEGER NOT NULL DEFAULT 0',
    'risk_level': 'INTEGER NOT NULL DEFAULT 50',
    'quality': 'INTEGER NOT NULL DEFAULT 50',
    'compliance': 'INTEGER NOT NULL DEFAULT 50',
    'ending': "TEXT NOT NULL DEFAULT ''",
    'final_report': "TEXT NOT NULL DEFAULT ''",
}
FILE_COLUMNS = {
    'attempt_id': 'INTEGER REFERENCES attempts(id)',
    'step_id': 'INTEGER REFERENCES scenario_steps(id)',
    'purpose': "TEXT NOT NULL DEFAULT 'general'",
}

def get_db():
    if 'db' not in g:
        path = Path(current_app.config['DATABASE_PATH'])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def _add_columns(db, table, columns):
    existing = {row['name'] for row in db.execute(f'PRAGMA table_info({table})').fetchall()}
    for name, ddl in columns.items():
        if name not in existing:
            db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')

def init_db():
    db = get_db()
    for statement in SCHEMA:
        db.execute(statement)
    _add_columns(db, 'attempts', ATTEMPT_COLUMNS)
    _add_columns(db, 'uploaded_files', FILE_COLUMNS)
    db.commit()

def seed_demo_data():
    db = get_db()
    now = '2026-06-05 12:00:00'
    if db.execute('SELECT COUNT(*) FROM roles').fetchone()[0] == 0:
        roles = [('admin', 'Администратор', 'Полный доступ к панели администратора и настройкам.'), ('teacher', 'Преподаватель', 'Управление сценариями и анализ результатов.'), ('student', 'Студент', 'Прохождение симуляторов, загрузка артефактов и получение отчетов.')]
        db.executemany('INSERT INTO roles(code, name, description) VALUES (?, ?, ?)', roles)
        role_map = {row['code']: row['id'] for row in db.execute('SELECT * FROM roles').fetchall()}
        users = [('admin', generate_password_hash('admin123'), 'Нилова Мария Олеговна', 'admin@edusim.local', role_map['admin'], now, 1), ('teacher', generate_password_hash('teacher123'), 'Преподаватель демо', 'teacher@edusim.local', role_map['teacher'], now, 1), ('student', generate_password_hash('student123'), 'Студент демо', 'student@edusim.local', role_map['student'], now, 1)]
        db.executemany('INSERT INTO users(username,password_hash,full_name,email,role_id,created_at,is_active) VALUES (?,?,?,?,?,?,?)', users)
        settings = [('site_name', 'EduSim', 'Название сетевого ресурса'), ('author', 'Нилова Мария Олеговна', 'ФИО автора ВКР'), ('support_email', 'support@edusim.local', 'Почта службы поддержки'), ('max_upload_mb', '8', 'Максимальный размер файла'), ('default_language', 'ru', 'Язык интерфейса')]
        db.executemany('INSERT INTO settings(key,value,description) VALUES (?,?,?)', settings)
        scenario_rows = [('Симулятор внедрения информационной системы', 'is-implementation', 'Средний', 25, 'Ветвящийся сценарий принятия управленческих решений при внедрении ИС.', 'Научиться оценивать требования, риски, документы и последствия решений.', 1), ('Симулятор реагирования на инцидент', 'incident-response', 'Сложный', 30, 'Сценарий анализа инцидента, коммуникаций и восстановления сервиса.', 'Освоить последовательность действий при нарушении доступности сервиса.', 1), ('Симулятор проектного бюджета', 'project-budget', 'Начальный', 20, 'Сценарий распределения бюджета проекта с учетом качества, сроков и рисков.', 'Понять влияние управленческих решений на итог проекта.', 1)]
        db.executemany('INSERT INTO scenarios(title,slug,difficulty,duration_minutes,summary,learning_goal,is_public) VALUES (?,?,?,?,?,?,?)', scenario_rows)
        scenarios = {row['slug']: row['id'] for row in db.execute('SELECT * FROM scenarios').fetchall()}
        module_rows = []
        for slug, scenario_id in scenarios.items():
            module_rows.extend([
                (scenario_id, 'Описание симуляции', 'Сценарий содержит состояние, развилки и последствия выбора. Баллы зависят не от угадывания ответа, а от качества управленческих действий.', 1),
                (scenario_id, 'Работа с файлами', 'Файлы используются как артефакты решения: техническое задание, отчет, акт проверки или план коммуникаций. Без нужного файла отдельные этапы не завершаются.', 2),
                (scenario_id, 'Итоговый отчет', 'После завершения формируется отчет с историей решений, изменением риска, бюджета, сроков и качества.', 3),
            ])
        db.executemany('INSERT INTO modules(scenario_id,title,content,sort_order) VALUES (?,?,?,?)', module_rows)
        articles = [('Методика обучения через симуляции', 'methodology', 'Симулятор закрепляет знания через практические ситуации, где обучающийся видит последствия каждого решения.', now), ('Как устроен сценарий', 'scenario-design', 'Каждый сценарий состоит из этапов, состояния, вариантов действий, переходов, файловых артефактов и итогового отчета.', now), ('Роли пользователей', 'roles', 'Администратор управляет ресурсом, преподаватель анализирует результаты, студент проходит обучение.', now)]
        db.executemany('INSERT INTO articles(title,slug,body,published_at) VALUES (?,?,?,?)', articles)
        db.execute("INSERT INTO activity_logs(user_id, action, details, created_at) VALUES (NULL, 'seed', 'Созданы демонстрационные данные', ?)", (now,))
    _seed_simulation_steps(db)
    db.commit()

def _seed_simulation_steps(db):
    scenarios = db.execute('SELECT id, title, slug FROM scenarios ORDER BY id').fetchall()
    for scenario in scenarios:
        sid = scenario['id']
        if db.execute('SELECT COUNT(*) FROM scenario_steps WHERE scenario_id=?', (sid,)).fetchone()[0] > 0:
            continue
        steps = [
            ('start', 'Вводная ситуация', f'Начинается сценарий «{scenario["title"]}». Данные неполные, сроки ограничены, решения студента будут менять состояние проекта. Нужно выбрать первый шаг.', 0, '', 1),
            ('requirements', 'Анализ условий', 'После первого действия появились уточнения. Необходимо зафиксировать требования, ограничения или план работ, чтобы решение можно было проверить.', 1, 'Загрузите файл-артефакт: ТЗ, перечень требований, план действий или краткий отчет. Подойдут PDF, DOCX, TXT, PNG, JPG.', 2),
            ('pilot', 'Проверка решения', 'Команда подготовила рабочий вариант. Есть риск, что решение не подойдет пользователям или не пройдет проверку преподавателя.', 0, '', 3),
            ('incident', 'Нештатная ситуация', 'На этапе запуска возникла проблема. Нужно доказательно описать ситуацию и выбрать корректное управленческое действие.', 1, 'Загрузите отчет, скриншот ошибки или другой файл, подтверждающий анализ проблемы.', 4),
            ('finish', 'Итог', 'Симуляция завершена. Система рассчитывает результат по истории решений.', 0, '', 5),
        ]
        step_ids = {}
        for code, title, context, req, instr, order in steps:
            cur = db.execute('INSERT INTO scenario_steps(scenario_id,code,title,context,file_required,file_instruction,sort_order) VALUES (?,?,?,?,?,?,?)', (sid, code, title, context, req, instr, order))
            step_ids[code] = cur.lastrowid
        choices = {
            'start': [
                ('Сразу перейти к реализации', 'Работа началась быстро, но без согласованных границ риск вырос.', 'requirements', 8, 20000, 15, -10, -5, 5),
                ('Провести интервью и определить критерии успеха', 'Контекст стал понятнее, риск снизился, но потребовалось больше времени.', 'requirements', 16, 12000, -10, 15, 10, 18),
                ('Использовать готовое решение без анализа', 'Решение быстрое, но оно может не подойти под учебную задачу.', 'pilot', 6, 80000, 10, -5, 0, 8),
            ],
            'requirements': [
                ('Загрузить документ и согласовать минимальный набор работ', 'Файл стал артефактом этапа. Появилась основа для контроля результата.', 'pilot', 12, 10000, -12, 15, 15, 20),
                ('Оставить договоренности только в переписке', 'Решение не фиксирует ответственность. При споре сложно доказать состав работ.', 'pilot', 4, 0, 18, -15, -15, 3),
            ],
            'pilot': [
                ('Провести пилот на небольшой группе и собрать UX-оценку', 'Пользовательская проверка выявила проблемы до полного запуска.', 'incident', 14, 15000, -10, 15, 10, 20),
                ('Запустить сразу на всех пользователей', 'Сроки сокращены, но вырос риск массовых ошибок.', 'incident', 4, 5000, 20, -10, -5, 5),
                ('Отложить запуск до полной переработки интерфейса', 'Качество выросло, но сроки и бюджет заметно увеличились.', 'incident', 30, 30000, -5, 10, 5, 12),
            ],
            'incident': [
                ('Загрузить отчет, выделить причину и временное решение', 'Проблема зафиксирована, риск снижен, коммуникация стала прозрачной.', 'finish', 8, 7000, -15, 10, 15, 22),
                ('Сообщить, что проблемы нет', 'Игнорирование инцидента ухудшило доверие пользователей и качество результата.', 'finish', 2, 0, 25, -20, -20, 0),
            ],
        }
        for code, rows in choices.items():
            for row in rows:
                db.execute('''INSERT INTO scenario_choices(step_id,text,feedback,next_step_code,delta_time,delta_budget,delta_risk,delta_quality,delta_compliance,score)
                              VALUES (?,?,?,?,?,?,?,?,?,?)''', (step_ids[code],) + row)
