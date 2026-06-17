from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from .database import get_db
from .forms import validate_required, validate_email, clean_text
public_bp = Blueprint('public', __name__)
PUBLIC_PAGES = {'about': {'title': 'О проекте', 'template': 'public/about.html'}, 'methodology': {'title': 'Методика', 'template': 'public/methodology.html'}, 'cases': {'title': 'Учебные кейсы', 'template': 'public/cases.html'}, 'faq': {'title': 'FAQ', 'template': 'public/faq.html'}, 'contacts': {'title': 'Контакты', 'template': 'public/contacts.html'}, 'help': {'title': 'Справка', 'template': 'public/help.html'}, 'accessibility': {'title': 'Доступность', 'template': 'public/accessibility.html'}, 'privacy': {'title': 'Данные', 'template': 'public/privacy.html'}}

@public_bp.route('/')
def index():
    scenarios = get_db().execute('SELECT * FROM scenarios WHERE is_public=1 ORDER BY id').fetchall()
    return render_template('public/index.html', scenarios=scenarios, breadcrumbs=[('Главная', None)])

@public_bp.route('/scenarios')
def scenarios():
    rows = get_db().execute('SELECT * FROM scenarios WHERE is_public=1 ORDER BY difficulty, title').fetchall()
    return render_template('public/scenarios.html', scenarios=rows, breadcrumbs=[('Главная', '/'), ('Сценарии', None)])

@public_bp.route('/scenario/<slug>')
def scenario_detail(slug):
    db = get_db()
    scenario = db.execute('SELECT * FROM scenarios WHERE slug=?', (slug,)).fetchone()
    if not scenario:
        return (render_template('errors/404.html'), 404)
    modules = db.execute('SELECT * FROM modules WHERE scenario_id=? ORDER BY sort_order', (scenario['id'],)).fetchall()
    return render_template('public/scenario_detail.html', scenario=scenario, modules=modules, breadcrumbs=[('Главная', '/'), ('Сценарии', url_for('public.scenarios')), (scenario['title'], None)])

@public_bp.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        errors = validate_required(request.form, ['name', 'email', 'topic', 'message'])
        if not validate_email(request.form.get('email', '')):
            errors.append('Укажите корректный e-mail')
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            get_db().execute('INSERT INTO feedback(name,email,topic,message,status,created_at) VALUES (?,?,?,?,?,?)', (clean_text(request.form['name'], 120), clean_text(request.form['email'], 160), clean_text(request.form['topic'], 160), clean_text(request.form['message'], 2000), 'new', datetime.now().isoformat(timespec='seconds')))
            get_db().commit()
            flash('Сообщение отправлено. Администратор увидит его в панели управления.', 'success')
            return redirect(url_for('public.feedback'))
    return render_template('public/feedback.html', breadcrumbs=[('Главная', '/'), ('Обратная связь', None)])

@public_bp.route('/page/<slug>')
def page(slug):
    page_info = PUBLIC_PAGES.get(slug)
    if not page_info:
        return (render_template('errors/404.html'), 404)
    return render_template(page_info['template'], title=page_info['title'], breadcrumbs=[('Главная', '/'), (page_info['title'], None)])

@public_bp.route('/checklist')
def checklist():
    return render_template('public/checklist.html', title='Чек-лист', breadcrumbs=[('Главная', '/'), ('Чек-лист', None)])
