from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from .database import get_db
from .security import roles_required, current_user
from .forms import clean_text
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@roles_required('admin')
def dashboard():
    db = get_db()
    stats = {'users': db.execute('SELECT COUNT(*) FROM users').fetchone()[0], 'scenarios': db.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0], 'attempts': db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0], 'feedback': db.execute("SELECT COUNT(*) FROM feedback WHERE status='new'").fetchone()[0]}
    return render_template('admin/dashboard.html', stats=stats, breadcrumbs=[('Главная', '/'), ('Администрирование', None)])

@admin_bp.route('/users')
@roles_required('admin')
def users():
    rows = get_db().execute('SELECT u.*, r.name AS role_name FROM users u JOIN roles r ON r.id=u.role_id ORDER BY u.id').fetchall()
    return render_template('admin/users.html', users=rows, breadcrumbs=[('Главная', '/'), ('Администрирование', url_for('admin.dashboard')), ('Пользователи', None)])

@admin_bp.route('/scenarios', methods=['GET', 'POST'])
@roles_required('admin')
def scenarios():
    db = get_db()
    if request.method == 'POST':
        db.execute('INSERT INTO scenarios(title,slug,difficulty,duration_minutes,summary,learning_goal,is_public) VALUES (?,?,?,?,?,?,1)', (clean_text(request.form.get('title'), 180), clean_text(request.form.get('slug'), 120), clean_text(request.form.get('difficulty'), 60), int(request.form.get('duration_minutes', 20)), clean_text(request.form.get('summary'), 500), clean_text(request.form.get('learning_goal'), 500)))
        db.commit()
        flash('Сценарий добавлен.', 'success')
        return redirect(url_for('admin.scenarios'))
    rows = db.execute('SELECT * FROM scenarios ORDER BY id').fetchall()
    return render_template('admin/scenarios.html', scenarios=rows, breadcrumbs=[('Главная', '/'), ('Администрирование', url_for('admin.dashboard')), ('Сценарии', None)])

@admin_bp.route('/feedback')
@roles_required('admin')
def feedback():
    rows = get_db().execute('SELECT * FROM feedback ORDER BY id DESC').fetchall()
    return render_template('admin/feedback.html', feedback=rows, breadcrumbs=[('Главная', '/'), ('Администрирование', url_for('admin.dashboard')), ('Обратная связь', None)])

@admin_bp.route('/logs')
@roles_required('admin')
def logs():
    rows = get_db().execute('SELECT l.*, u.username FROM activity_logs l LEFT JOIN users u ON u.id=l.user_id ORDER BY l.id DESC LIMIT 100').fetchall()
    return render_template('admin/logs.html', logs=rows, breadcrumbs=[('Главная', '/'), ('Администрирование', url_for('admin.dashboard')), ('Журнал', None)])

@admin_bp.route('/files')
@roles_required('admin')
def files():
    rows = get_db().execute('SELECT f.*, u.username FROM uploaded_files f JOIN users u ON u.id=f.user_id ORDER BY f.id DESC').fetchall()
    return render_template('admin/files.html', files=rows, breadcrumbs=[('Главная', '/'), ('Администрирование', url_for('admin.dashboard')), ('Файлы', None)])

@admin_bp.route('/settings', methods=['GET', 'POST'])
@roles_required('admin')
def settings():
    db = get_db()
    if request.method == 'POST':
        for key, value in request.form.items():
            db.execute('UPDATE settings SET value=? WHERE key=?', (clean_text(value, 500), key))
        db.execute('INSERT INTO activity_logs(user_id,action,details,created_at) VALUES (?,?,?,?)', (current_user()['id'], 'settings', 'Обновлены настройки', datetime.now().isoformat(timespec='seconds')))
        db.commit()
        flash('Настройки сохранены.', 'success')
    rows = db.execute('SELECT * FROM settings ORDER BY key').fetchall()
    return render_template('admin/settings.html', settings=rows, breadcrumbs=[('Главная', '/'), ('Администрирование', url_for('admin.dashboard')), ('Настройки', None)])
