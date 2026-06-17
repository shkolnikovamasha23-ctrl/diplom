from functools import wraps
from flask import abort, redirect, session, url_for, flash
from .database import get_db

def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return get_db().execute('SELECT u.*, r.code AS role_code, r.name AS role_name FROM users u JOIN roles r ON r.id=u.role_id WHERE u.id=?', (user_id,)).fetchone()

def login_required(view):

    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            flash('Для доступа к разделу необходимо войти в систему.', 'warning')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapper

def roles_required(*roles):

    def decorator(view):

        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                flash('Для доступа к разделу необходимо войти в систему.', 'warning')
                return redirect(url_for('auth.login'))
            if user['role_code'] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator
