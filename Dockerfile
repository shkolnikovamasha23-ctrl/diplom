FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p edusim/static/uploads edusim/generated edusim/data edusim/exports
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "main:app"]
