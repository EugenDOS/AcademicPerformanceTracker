# Academic Performance Tracker

Простое Django/DRF-приложение для ведения списков успеваемости и посещаемости.

## Что реализовано

- роли пользователей: администратор, преподаватель, студент;
- JWT-аутентификация для REST API;
- Swagger/OpenAPI-документация;
- модели групп, предметов, занятий, посещаемости и оценок;
- API в формате JSON;
- простые HTML-страницы по MVT: панель, группы, предметы, занятия, оценки, посещаемость;
- PostgreSQL как основная СУБД.

## Запуск с PostgreSQL

```powershell
.\venv\Scripts\pip.exe install -r requirements.txt

$env:POSTGRES_DB="academic_performance_tracker"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"

.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py seed_demo
.\venv\Scripts\python.exe manage.py runserver
```

## Быстрая локальная проверка без PostgreSQL

```powershell
$env:USE_SQLITE="1"
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py seed_demo
.\venv\Scripts\python.exe manage.py runserver
```

Демо-пользователи после `seed_demo`:

- `admin / admin12345`
- `teacher / teacher12345`
- `student / student12345`

## API

- `POST /api/token/` - получить JWT access/refresh;
- `POST /api/token/refresh/` - обновить access token;
- `GET /api/schema/` - OpenAPI-схема;
- `GET /api/docs/` - Swagger UI;
- `GET /api/me/` - текущий пользователь;
- `/api/users/`
- `/api/groups/`
- `/api/subjects/`
- `/api/lessons/`
- `/api/attendance/`
- `/api/grades/`

Администратор видит и меняет все данные. Преподаватель меняет свои занятия, оценки и посещаемость. Студент видит только свои оценки, посещаемость и занятия своей группы.
