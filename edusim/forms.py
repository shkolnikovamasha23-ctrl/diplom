import re
EMAIL_RE = re.compile('^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')

def validate_required(data, fields):
    errors = []
    for field in fields:
        if not str(data.get(field, '')).strip():
            errors.append(f'Поле {field} обязательно для заполнения')
    return errors

def validate_email(email):
    return bool(EMAIL_RE.match(email or ''))

def clean_text(value, limit=2000):
    value = (value or '').strip()
    return value[:limit]
