
# GO Acquaintances Bot

Telegram бот знакомств с админ-панелью и AI модерацией.

## Возможности

- Регистрация и профили пользователей
- Система лайков и совпадений
- AI модерация контента
- Админ-панель через Telegram Mini App
- Система рефералов
- Буст-анкеты

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/GO_Acquaintances_Bot.git
cd GO_Acquaintances_Bot
```

2. Создайте виртуальное окружение:
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл и добавьте свои значения
```

5. Запустите бота:
```bash
python main.py
```

## Структура проекта

- `main.py` - точка входа приложения
- `config.py` - конфигурация
- `handlers/` - обработчики команд и сообщений
- `database/` - модели и репозитории базы данных
- `services/` - бизнес-логика
- `admin_panel/` - админ-панель (Mini App)

## Документация

Подробная документация по развертыванию находится в файле [DEPLOYMENT.md](DEPLOYMENT.md).

## Лицензия

[Укажите вашу лицензию]