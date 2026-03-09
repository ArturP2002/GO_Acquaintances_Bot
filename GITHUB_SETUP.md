# Инструкция по переносу проекта в GitHub

Эта инструкция поможет вам перенести проект GO_Acquaintances_Bot в репозиторий на GitHub.

## Содержание

1. [Подготовка проекта](#1-подготовка-проекта)
2. [Создание репозитория на GitHub](#2-создание-репозитория-на-github)
3. [Инициализация Git и первый коммит](#3-инициализация-git-и-первый-коммит)
4. [Настройка .env.example](#4-настройка-envexample)
5. [Создание README.md](#5-создание-readmemd)
6. [Дополнительные настройки](#6-дополнительные-настройки)

---

## 1. Подготовка проекта

### 1.1 Создание файла .gitignore

Создайте файл `.gitignore` в корне проекта со следующим содержимым:

```bash
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Виртуальное окружение
venv/
env/
ENV/
.venv

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store

# База данных
*.db
*.sqlite
*.sqlite3

# Логи
*.log
logs/
bot.log

# Переменные окружения и секреты
.env
.env.local
.env.*.local
*.key
*.pem

# Node.js (для фронтенда)
admin_panel/mini_app/frontend/node_modules/
admin_panel/mini_app/frontend/dist/
admin_panel/mini_app/frontend/build/
admin_panel/mini_app/frontend/.vite/
admin_panel/mini_app/frontend/.env
admin_panel/mini_app/frontend/.env.local
admin_panel/mini_app/frontend/*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Временные файлы
*.tmp
*.temp
.cache/

# Системные файлы
Thumbs.db
.DS_Store
```

### 1.2 Проверка файлов перед коммитом

Убедитесь, что следующие файлы **НЕ** попадут в репозиторий:
- ✅ `.env` - файл с секретными данными
- ✅ `dating_bot.db` - база данных
- ✅ `bot.log` - файлы логов
- ✅ `venv/` - виртуальное окружение
- ✅ `__pycache__/` - кэш Python
- ✅ `admin_panel/mini_app/frontend/node_modules/` - зависимости Node.js

---

## 2. Создание репозитория на GitHub

### 2.1 Создание нового репозитория

1. Перейдите на [GitHub](https://github.com) и войдите в свой аккаунт
2. Нажмите на кнопку **"+"** в правом верхнем углу
3. Выберите **"New repository"**
4. Заполните форму:
   - **Repository name**: `GO_Acquaintances_Bot` (или другое имя)
   - **Description**: `Telegram бот знакомств на aiogram`
   - **Visibility**: выберите **Private** (рекомендуется) или **Public**
   - **НЕ** создавайте README, .gitignore или LICENSE (мы сделаем это локально)
5. Нажмите **"Create repository"**

### 2.2 Копирование URL репозитория

После создания репозитория GitHub покажет инструкции. Скопируйте URL вашего репозитория:
- HTTPS: `https://github.com/your-username/GO_Acquaintances_Bot.git`
- SSH: `git@github.com:your-username/GO_Acquaintances_Bot.git`

---

## 3. Инициализация Git и первый коммит

### 3.1 Инициализация Git репозитория

Откройте терминал в корне проекта и выполните:

```bash
# Переход в директорию проекта
cd /Users/arturprotasov/PycharmProjects/GO_Acquaintances_Bot

# Инициализация Git репозитория
git init

# Настройка имени пользователя и email (если еще не настроено глобально)
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 3.2 Добавление файлов в staging

```bash
# Добавление всех файлов (кроме тех, что в .gitignore)
git add .

# Проверка, какие файлы будут добавлены
git status
```

**Важно**: Убедитесь, что в списке нет:
- `.env`
- `dating_bot.db`
- `bot.log`
- `venv/`
- `node_modules/`

### 3.3 Создание первого коммита

```bash
# Создание первого коммита
git commit -m "Initial commit: Telegram dating bot with admin panel"
```

### 3.4 Добавление remote и отправка на GitHub

```bash
# Добавление remote репозитория (замените URL на ваш)
git remote add origin https://github.com/your-username/GO_Acquaintances_Bot.git

# Или если используете SSH:
# git remote add origin git@github.com:your-username/GO_Acquaintances_Bot.git

# Переименование основной ветки в main (если нужно)
git branch -M main

# Отправка кода на GitHub
git push -u origin main
```

Если вы используете HTTPS и GitHub попросит аутентификацию:
- Используйте **Personal Access Token** вместо пароля
- Создайте токен: Settings → Developer settings → Personal access tokens → Tokens (classic)
- Или используйте SSH ключи для более удобной работы

---

## 4. Настройка .env.example

Создайте файл `.env.example` в корне проекта как шаблон для других разработчиков:

```bash
# Создание файла .env.example
touch .env.example
```

Добавьте в `.env.example` следующий контент (без реальных значений):

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here

# Модерация
MODERATION_GROUP_ID=your_moderation_group_id
ADMIN_GROUP_ID=your_admin_group_id

# AI модерация (опционально)
OPENAI_API_KEY=your_openai_api_key
AI_MODEL=gpt-4o-mini

# Replicate API (опционально)
REPLICATE_API_KEY=your_replicate_api_key

# Лимиты и настройки
MAX_LIKES_PER_DAY=50
MIN_AGE=16
BOOST_FREQUENCY=15
REFERRAL_BONUS=10

# База данных
DATABASE_PATH=dating_bot.db

# Логирование
LOG_LEVEL=INFO
LOG_FILE=bot.log

# Инициализация owner
OWNER_TELEGRAM_ID=your_telegram_id

# Mini App
MINI_APP_URL=https://your-domain.com
```

Затем добавьте этот файл в репозиторий:

```bash
git add .env.example
git commit -m "Add .env.example template"
git push
```

---

## 5. Создание README.md

Создайте файл `README.md` с описанием проекта (если его еще нет):

```bash
# Создание README.md
touch README.md
```

Пример содержимого `README.md`:

```markdown
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
```

Добавьте README в репозиторий:

```bash
git add README.md
git commit -m "Add README.md"
git push
```

---

## 6. Дополнительные настройки

### 6.1 Настройка GitHub Actions (опционально)

Если хотите настроить CI/CD, создайте директорию:

```bash
mkdir -p .github/workflows
```

### 6.2 Защита секретов

**Важно**: Никогда не коммитьте файлы с секретами:
- ✅ `.env` - должен быть в `.gitignore`
- ✅ Любые файлы с API ключами
- ✅ Базы данных с реальными данными

### 6.3 Настройка GitHub Secrets (для CI/CD)

Если планируете использовать GitHub Actions, добавьте секреты:
1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте необходимые секреты (BOT_TOKEN, OPENAI_API_KEY и т.д.)

### 6.4 Добавление лицензии (опционально)

Если хотите добавить лицензию:

```bash
# Создание файла LICENSE
touch LICENSE
# Добавьте текст лицензии (MIT, Apache 2.0 и т.д.)
```

---

## Проверка успешного переноса

После выполнения всех шагов проверьте:

1. ✅ Репозиторий создан на GitHub
2. ✅ Все файлы загружены (кроме игнорируемых)
3. ✅ `.env.example` присутствует
4. ✅ `README.md` присутствует
5. ✅ `.gitignore` работает корректно
6. ✅ Секретные файлы не попали в репозиторий

Проверить содержимое репозитория можно на странице GitHub:
```
https://github.com/your-username/GO_Acquaintances_Bot
```

---

## Полезные команды Git

```bash
# Проверка статуса
git status

# Просмотр изменений
git diff

# Просмотр истории коммитов
git log

# Создание новой ветки
git checkout -b feature/new-feature

# Отправка ветки на GitHub
git push -u origin feature/new-feature

# Обновление локального репозитория
git pull origin main

# Просмотр remote репозиториев
git remote -v
```

---

## Решение проблем

### Проблема: Git просит аутентификацию при push

**Решение**: Используйте Personal Access Token или настройте SSH ключи.

### Проблема: Файлы из .gitignore все равно попадают в репозиторий

**Решение**: Если файлы уже были добавлены в Git до создания .gitignore:
```bash
git rm --cached filename
git commit -m "Remove tracked file"
```

### Проблема: Конфликт при push

**Решение**: 
```bash
git pull origin main --rebase
# Решите конфликты, если есть
git push
```

---

## Дополнительные ресурсы

- [Документация Git](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)
- [GitHub CLI](https://cli.github.com/) - альтернативный способ работы с GitHub

---

**Готово!** Ваш проект теперь на GitHub. 🎉
