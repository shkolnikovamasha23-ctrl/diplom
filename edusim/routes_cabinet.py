from datetime import datetime
from pathlib import Path
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename
from .database import get_db
from .security import login_required, current_user
from .forms import clean_text
from .documents import create_attempt_docx, create_attempts_xlsx
cabinet_bp = Blueprint('cabinet', __name__, url_prefix='/cabinet')

@cabinet_bp.route('/')
@login_required
def dashboard():
    user = current_user()
    db = get_db()
    attempts = db.execute('SELECT a.*, s.title AS scenario_title FROM attempts a JOIN scenarios s ON s.id=a.scenario_id WHERE a.user_id=? ORDER BY a.id DESC LIMIT 5', (user['id'],)).fetchall()
    achievements = db.execute('SELECT * FROM achievements WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    return render_template('cabinet/dashboard.html', user=user, attempts=attempts, achievements=achievements, breadcrumbs=[('Главная', '/'), ('Личный кабинет', None)])

@cabinet_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user()
    if request.method == 'POST':
        get_db().execute('UPDATE users SET full_name=?, email=? WHERE id=?', (clean_text(request.form.get('full_name'), 160), clean_text(request.form.get('email'), 160), user['id']))
        get_db().commit()
        flash('Профиль обновлен.', 'success')
        return redirect(url_for('cabinet.profile'))
    return render_template('cabinet/profile.html', user=user, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Профиль', None)])

@cabinet_bp.route('/simulator')
@login_required
def simulator():
    scenarios = get_db().execute('SELECT * FROM scenarios WHERE is_public=1 ORDER BY id').fetchall()
    return render_template('cabinet/simulator.html', scenarios=scenarios, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Симулятор', None)])


def _save_step_file(user_id, attempt_id, step_id, file_obj, purpose):
    if not file_obj or not file_obj.filename:
        return None
    safe = secure_filename(file_obj.filename)
    saved_name = f"{user_id}_{attempt_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}"
    path = Path(current_app.config['UPLOAD_FOLDER']) / saved_name
    file_obj.save(path)
    cur = get_db().execute(
        '''INSERT INTO uploaded_files(user_id,original_name,saved_name,file_size,uploaded_at,attempt_id,step_id,purpose)
           VALUES (?,?,?,?,?,?,?,?)''',
        (user_id, file_obj.filename, saved_name, path.stat().st_size, datetime.now().isoformat(timespec='seconds'), attempt_id, step_id, purpose)
    )
    return cur.lastrowid


def _finish_attempt(db, attempt_id):
    attempt = db.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
    score = attempt['score']
    risk = attempt['risk_level']
    quality = attempt['quality']
    compliance = attempt['compliance']
    if score >= 70 and risk <= 50 and quality >= 60 and compliance >= 60:
        ending = 'Успешное внедрение'
        report = 'Проект завершен устойчиво: решения были обоснованы, файлы использованы как артефакты, риски контролировались.'
    elif risk > 80 or quality < 35:
        ending = 'Проблемный запуск'
        report = 'Проект завершен с серьезными проблемами. Требуется повторная работа с требованиями, UX и управлением инцидентами.'
    else:
        ending = 'Частично успешное внедрение'
        report = 'Цель в целом достигнута, но отдельные решения увеличили затраты или риск. Нужен план доработок.'
    now = datetime.now().isoformat(timespec='seconds')
    db.execute('UPDATE attempts SET status=?, finished_at=?, ending=?, final_report=? WHERE id=?', ('finished', now, ending, report, attempt_id))
    return ending


@cabinet_bp.route('/simulator/<int:scenario_id>', methods=['GET', 'POST'])
@login_required
def run_scenario(scenario_id):
    user = current_user()
    db = get_db()
    scenario = db.execute('SELECT * FROM scenarios WHERE id=?', (scenario_id,)).fetchone()
    if not scenario:
        return (render_template('errors/404.html'), 404)

    attempt_id = request.args.get('attempt_id', type=int)
    attempt = None
    if attempt_id:
        attempt = db.execute('SELECT * FROM attempts WHERE id=? AND user_id=? AND scenario_id=?', (attempt_id, user['id'], scenario_id)).fetchone()

    if attempt is None:
        started = datetime.now().isoformat(timespec='seconds')
        cur = db.execute(
            '''INSERT INTO attempts(user_id,scenario_id,started_at,score,status,time_spent,budget_spent,risk_level,quality,compliance)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (user['id'], scenario_id, started, 0, 'started', 0, 0, 50, 50, 50)
        )
        db.commit()
        return redirect(url_for('cabinet.run_scenario', scenario_id=scenario_id, attempt_id=cur.lastrowid))

    if attempt['status'] == 'finished':
        return redirect(url_for('cabinet.attempt_detail', attempt_id=attempt['id']))

    last_event = db.execute('''SELECT e.*, c.next_step_code FROM simulation_events e
                               JOIN scenario_choices c ON c.id=e.choice_id
                               WHERE e.attempt_id=? ORDER BY e.id DESC LIMIT 1''', (attempt['id'],)).fetchone()
    next_code = last_event['next_step_code'] if last_event else 'start'
    step = db.execute('SELECT * FROM scenario_steps WHERE scenario_id=? AND code=?', (scenario_id, next_code)).fetchone()
    if not step or step['code'] == 'finish':
        ending = _finish_attempt(db, attempt['id'])
        if attempt['score'] >= 70:
            db.execute('INSERT INTO achievements(user_id,title,description,awarded_at) VALUES (?,?,?,?)', (user['id'], 'Успешная симуляция', f'Получен итог: {ending}', datetime.now().isoformat(timespec='seconds')))
        db.commit()
        return redirect(url_for('cabinet.attempt_detail', attempt_id=attempt['id']))

    choices = db.execute('SELECT * FROM scenario_choices WHERE step_id=? ORDER BY id', (step['id'],)).fetchall()

    if request.method == 'POST':
        choice_id = request.form.get('choice_id', type=int)
        choice = db.execute('SELECT * FROM scenario_choices WHERE id=? AND step_id=?', (choice_id, step['id'])).fetchone()
        if not choice:
            flash('Выберите действие для продолжения симуляции.', 'warning')
            return redirect(url_for('cabinet.run_scenario', scenario_id=scenario_id, attempt_id=attempt['id']))
        upload_id = _save_step_file(user['id'], attempt['id'], step['id'], request.files.get('evidence_file'), 'scenario_step')
        if step['file_required'] and not upload_id:
            flash('На этом этапе нужен файл-артефакт: отчет, ТЗ, скриншот или другой документ.', 'danger')
            return redirect(url_for('cabinet.run_scenario', scenario_id=scenario_id, attempt_id=attempt['id']))
        new_time = max(0, attempt['time_spent'] + choice['delta_time'])
        new_budget = max(0, attempt['budget_spent'] + choice['delta_budget'])
        new_risk = min(100, max(0, attempt['risk_level'] + choice['delta_risk']))
        new_quality = min(100, max(0, attempt['quality'] + choice['delta_quality']))
        new_compliance = min(100, max(0, attempt['compliance'] + choice['delta_compliance']))
        new_score = min(100, max(0, attempt['score'] + choice['score']))
        db.execute('''UPDATE attempts SET score=?, time_spent=?, budget_spent=?, risk_level=?, quality=?, compliance=? WHERE id=?''',
                   (new_score, new_time, new_budget, new_risk, new_quality, new_compliance, attempt['id']))
        db.execute('''INSERT INTO simulation_events(attempt_id,step_id,choice_id,uploaded_file_id,time_spent,budget_spent,risk_level,quality,compliance,created_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?)''',
                   (attempt['id'], step['id'], choice['id'], upload_id, new_time, new_budget, new_risk, new_quality, new_compliance, datetime.now().isoformat(timespec='seconds')))
        db.commit()
        flash(choice['feedback'], 'success')
        return redirect(url_for('cabinet.run_scenario', scenario_id=scenario_id, attempt_id=attempt['id']))

    events = db.execute('''SELECT e.*, st.title AS step_title, c.text AS choice_text, c.feedback, f.original_name
                           FROM simulation_events e
                           JOIN scenario_steps st ON st.id=e.step_id
                           JOIN scenario_choices c ON c.id=e.choice_id
                           LEFT JOIN uploaded_files f ON f.id=e.uploaded_file_id
                           WHERE e.attempt_id=? ORDER BY e.id''', (attempt['id'],)).fetchall()
    return render_template('cabinet/run_scenario.html', scenario=scenario, attempt=attempt, step=step, choices=choices, events=events, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Симулятор', url_for('cabinet.simulator')), (scenario['title'], None)])

@cabinet_bp.route('/attempts')
@login_required
def attempts():
    user = current_user()
    rows = get_db().execute('SELECT a.*, s.title AS scenario_title FROM attempts a JOIN scenarios s ON s.id=a.scenario_id WHERE a.user_id=? ORDER BY a.id DESC', (user['id'],)).fetchall()
    return render_template('cabinet/attempts.html', attempts=rows, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Попытки', None)])

@cabinet_bp.route('/attempt/<int:attempt_id>')
@login_required
def attempt_detail(attempt_id):
    user = current_user()
    db = get_db()
    attempt = db.execute('SELECT a.*, s.title AS scenario_title FROM attempts a JOIN scenarios s ON s.id=a.scenario_id WHERE a.id=? AND a.user_id=?', (attempt_id, user['id'])).fetchone()
    answers = db.execute('SELECT q.text, q.explanation, o.text AS option_text, ans.is_correct FROM answers ans JOIN questions q ON q.id=ans.question_id JOIN options o ON o.id=ans.option_id WHERE ans.attempt_id=?', (attempt_id,)).fetchall()
    events = db.execute('''SELECT e.*, st.title AS step_title, c.text AS choice_text, c.feedback, f.original_name
                           FROM simulation_events e
                           JOIN scenario_steps st ON st.id=e.step_id
                           JOIN scenario_choices c ON c.id=e.choice_id
                           LEFT JOIN uploaded_files f ON f.id=e.uploaded_file_id
                           WHERE e.attempt_id=? ORDER BY e.id''', (attempt_id,)).fetchall()
    return render_template('cabinet/attempt_detail.html', attempt=attempt, answers=answers, events=events, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Попытки', url_for('cabinet.attempts')), ('Результат', None)])

@cabinet_bp.route('/files', methods=['GET', 'POST'])
@login_required
def files():
    user = current_user()
    db = get_db()
    if request.method == 'POST' and 'file' in request.files:
        f = request.files['file']
        if f.filename:
            safe = secure_filename(f.filename)
            saved_name = f"{user['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}"
            path = Path(current_app.config['UPLOAD_FOLDER']) / saved_name
            f.save(path)
            db.execute('INSERT INTO uploaded_files(user_id,original_name,saved_name,file_size,uploaded_at) VALUES (?,?,?,?,?)', (user['id'], f.filename, saved_name, path.stat().st_size, datetime.now().isoformat(timespec='seconds')))
            db.commit()
            flash('Файл загружен в файловое хранилище проекта.', 'success')
    rows = db.execute('SELECT * FROM uploaded_files WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    return render_template('cabinet/files.html', files=rows, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Файлы', None)])

@cabinet_bp.route('/achievements')
@login_required
def achievements():
    user = current_user()
    rows = get_db().execute('SELECT * FROM achievements WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    return render_template('cabinet/achievements.html', achievements=rows, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Достижения', None)])

@cabinet_bp.route('/documents')
@login_required
def documents():
    user = current_user()
    rows = get_db().execute('SELECT * FROM generated_documents WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall()
    return render_template('cabinet/documents.html', documents=rows, breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Документы', None)])

@cabinet_bp.route('/documents/xlsx')
@login_required
def export_xlsx():
    path = create_attempts_xlsx(current_user())
    return send_file(path, as_attachment=True)

@cabinet_bp.route('/documents/docx/<int:attempt_id>')
@login_required
def export_docx(attempt_id):
    path = create_attempt_docx(current_user(), attempt_id)
    return send_file(path, as_attachment=True)

@cabinet_bp.route('/settings')
@login_required
def settings():
    return render_template('cabinet/settings.html', user=current_user(), breadcrumbs=[('Главная', '/'), ('Личный кабинет', url_for('cabinet.dashboard')), ('Настройки', None)])
