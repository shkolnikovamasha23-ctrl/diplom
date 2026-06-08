# Соответствие требованиям индивидуального задания

| Требование | Реализация в проекте |
|---|---|
| Python + Django/Flask | Flask-приложение, `main.py` в корне |
| Не менее 10 публичных страниц | Главная, сценарии, карточка сценария, о проекте, методика, кейсы, FAQ, контакты, справка, доступность, данные, обратная связь |
| Верхнее/боковое меню, хлебные крошки | `base.html` |
| Форма обратной связи | `/feedback`, таблица `feedback` |
| SQL-СУБД, не менее 10 таблиц | SQLite, 15 таблиц в `database.py` |
| Доступ к файловой системе | `/cabinet/files`, сохранение в `static/uploads` |
| DOCX/XLSX | `documents.py`, маршруты `/cabinet/documents/docx/*`, `/cabinet/documents/xlsx` |
| 3 роли | admin, teacher, student |
| Панель администратора 5+ страниц | dashboard, users, scenarios, feedback, logs, files, settings |
| Личный кабинет 5+ страниц | dashboard, profile, simulator, attempts, achievements, documents, files, settings |
| Адаптивность | CSS media queries |
| ФИО в подвале и справке | `base.html`, `/page/help` |
| Docker | Dockerfile и docker-compose.yml |
