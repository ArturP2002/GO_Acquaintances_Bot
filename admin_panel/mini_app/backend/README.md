# Admin Panel Backend

FastAPI backend для админ-панели Telegram бота знакомств.

## Технологии

- FastAPI
- Uvicorn
- Pydantic
- Peewee ORM

## Установка

```bash
# Для macOS используйте pip3
pip3 install -r requirements.txt
```

## Запуск

**Способ 1: Через скрипт (рекомендуется)**
```bash
python3 run.py
```

**Способ 2: Через main.py**
```bash
python3 main.py
```

**Способ 3: Через uvicorn напрямую**
```bash
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Примечание для macOS:** Используйте `python3` вместо `python`.

API будет доступно по адресу `http://localhost:8000`

## API Документация

После запуска сервера документация доступна по адресам:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Структура проекта

```
backend/
├── main.py              # Точка входа FastAPI приложения
├── dependencies.py      # Зависимости (авторизация, права доступа)
├── schemas.py           # Pydantic схемы для валидации
└── routers/             # API роутеры
    ├── users.py         # Управление пользователями
    ├── complaints.py    # Управление жалобами
    ├── settings.py      # Управление настройками
    └── boost.py         # Управление бустами
```

## Авторизация

API использует Bearer токен авторизации. В продакшене необходимо реализовать проверку подписи `initData` от Telegram Mini App.

Текущая реализация (для разработки):
- Токен передается в заголовке `Authorization: Bearer <telegram_id>`
- В продакшене нужно декодировать и проверить подпись `initData`

## Роли администраторов

- **owner** - полный доступ ко всем функциям
- **admin** - доступ к управлению пользователями, настройками, бустами
- **moderator** - доступ к жалобам и банам
- **support** - только просмотр

## Endpoints

### Пользователи (`/api/users`)
- `GET /` - список пользователей с фильтрацией
- `GET /{user_id}` - информация о пользователе
- `GET /{user_id}/profile` - профиль пользователя
- `PATCH /{user_id}` - обновление пользователя
- `POST /{user_id}/ban` - бан пользователя
- `POST /{user_id}/unban` - разбан пользователя
- `POST /{user_id}/reset-likes` - сброс лайков

### Жалобы (`/api/complaints`)
- `GET /` - список жалоб с фильтрацией
- `GET /{complaint_id}` - информация о жалобе
- `PATCH /{complaint_id}` - обновление статуса жалобы
- `POST /{complaint_id}/ban-reported` - бан пользователя по жалобе
- `GET /pending/count` - количество ожидающих жалоб

### Настройки (`/api/settings`)
- `GET /` - все настройки
- `GET /{key}` - настройка по ключу
- `PUT /{key}` - обновление настройки
- `DELETE /{key}` - удаление настройки

### Бусты (`/api/boost`)
- `POST /` - создание буста
- `GET /user/{user_id}` - все бусты пользователя
- `GET /user/{user_id}/active` - активные бусты пользователя
- `DELETE /{boost_id}` - удаление буста
