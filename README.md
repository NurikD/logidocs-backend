# KumAryk — Backend

Django REST API и веб-панель администратора для KumAryk — сервиса учёта транспортных документов (Путёвка, Дозвол) для клиентов грузоперевозок.

Клиенты видят свои документы через мобильное приложение ([репозиторий фронтенда](https://github.com/NurikD/logidocs)), диспетчер управляет клиентами и документами через adminui и получает push-уведомления обо всех истекающих путёвках.

## Возможности

- **REST API** (JWT-авторизация) для мобильного приложения: документы, автомобили, регистрация устройств.
- **adminui** — веб-панель для диспетчера (HTMX + Tailwind, без сборки фронтенда): клиенты, документы, автомобили, приглашения по одноразовой ссылке.
- **Срок действия Путёвки** считается автоматически: 2 месяца от даты оформления.
- **Push-уведомления** через Firebase Cloud Messaging — клиенту при истечении путёвки, диспетчеру — ежедневный дайджест по всем клиентам в зоне риска.
- Несколько автомобилей на одного клиента (опционально) — документы можно привязать к конкретной машине.

## Стек

Python 3.12, Django 5.2, Django REST Framework, SimpleJWT, django-cors-headers, firebase-admin, SQLite.

## Локальный запуск

```bash
git clone https://github.com/NurikD/logidocs-backend.git
cd logidocs-backend
git checkout deploy   # основная ветка разработки

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

По умолчанию (без переменных окружения) сервер работает в режиме разработки: `DEBUG=True`, база — `db.sqlite3`, push-уведомления печатаются в консоль (`--dry-run`), если не задан `FIREBASE_CREDENTIALS_PATH`.

## Переменные окружения (прод)

| Переменная | Назначение |
|---|---|
| `DJANGO_DEBUG` | `False` в проде (по умолчанию `True`) |
| `DJANGO_ALLOWED_HOSTS` | домены через запятую, например `kumaryk.pythonanywhere.com` |
| `DJANGO_SECRET_KEY` | секретный ключ Django, свой на каждую среду |
| `FIREBASE_CREDENTIALS_PATH` | путь к сервисному JSON-ключу Firebase Admin SDK (в `.gitignore`, не коммитится) |

## API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/auth/token/` | вход (логин/пароль → JWT) |
| POST | `/api/auth/change-password/` | смена пароля |
| GET | `/api/vehicles/` | автомобили текущего пользователя |
| GET | `/api/documents/` | документы (свои у клиента, все у диспетчера) |
| GET | `/api/documents/expiring/` | документы в зоне риска по всем клиентам (только диспетчер) |
| GET | `/api/documents/<id>/` | документ с файлами |
| POST | `/api/documents/<id>/dismiss-notification/` | клиент подтвердил уведомление об истечении |
| POST | `/api/devices/register/` | регистрация FCM-токена устройства |

Полный список маршрутов — `core/urls.py`.

## adminui

Веб-панель диспетчера: `/admin-ui/users/` (вход — учётка суперпользователя). Список клиентов, карточка клиента с документами и автомобилями, создание/удаление документов, страница истекающих путёвок (`/admin-ui/expiring/`).

## Push-уведомления

Ежедневная рассылка — management-команда, запускается по расписанию (cron / Scheduled Tasks на PythonAnywhere):

```bash
python manage.py send_expiry_notifications
```

Флаг `--dry-run` — не отправлять, только показать, что ушло бы (полезно без настроенного `FIREBASE_CREDENTIALS_PATH`).

## Структура проекта

```
core/       # настройки Django, корневые urls
accounts/   # модели (User, Document, Vehicle, DeviceToken), REST API, management-команды
adminui/    # веб-панель диспетчера (views, forms, templates)
```

## Деплой

Сейчас развёрнут на PythonAnywhere: `kumaryk.pythonanywhere.com`.
