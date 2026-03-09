# 🔄 Инструкция по обновлению проекта через GitHub

Подробная инструкция по обновлению файлов проекта на сервере через GitHub.

---

## 📋 Содержание

1. [Список измененных файлов](#1-список-измененных-файлов)
2. [Подготовка изменений локально](#2-подготовка-изменений-локально)
3. [Отправка изменений в GitHub](#3-отправка-изменений-в-github)
4. [Обновление на сервере](#4-обновление-на-сервере)
5. [Изменение OWNER_TELEGRAM_ID](#5-изменение-owner_telegram_id)
6. [Проверка после обновления](#6-проверка-после-обновления)
7. [Решение проблем](#7-решение-проблем)

---

## 1. Список измененных файлов

Ниже перечислены все файлы, которые были изменены или добавлены в последнем обновлении:

### Новые файлы:
- `tasks/freeze_inactive_profiles.py` - Задача автоматической заморозки неактивных анкет
- `GITHUB_UPDATE.md` - Инструкция по обновлению через GitHub

### Измененные файлы:

#### Функциональность заморозки неактивных анкет:
- `database/repositories/profile_repo.py` - Добавлен фильтр `is_active == True` в метод `get_candidates_for_user`
- `database/repositories/user_repo.py` - Обновлен метод `update_last_active` для автоматической разморозки
- `loader.py` - Добавлена регистрация задачи `freeze_inactive_profiles_task` в планировщик
- `tasks/__init__.py` - Добавлен экспорт новой задачи `freeze_inactive_profiles_task`

#### Функциональность бэкапа базы данных:
- `keyboards/inline/admin_keyboard.py` - Добавлена кнопка "💾 Бэкап БД" в главное меню админ-панели
- `handlers/admin/admin_commands.py` - Добавлен обработчик `admin_backup_database` для создания бэкапа БД

### Полный список путей к файлам:

```
tasks/freeze_inactive_profiles.py
database/repositories/profile_repo.py
database/repositories/user_repo.py
loader.py
tasks/__init__.py
keyboards/inline/admin_keyboard.py
handlers/admin/admin_commands.py
GITHUB_UPDATE.md
```

### Проверка измененных файлов перед коммитом:

```bash
# Посмотрите статус всех измененных файлов
git status

# Посмотрите изменения в конкретном файле
git diff tasks/freeze_inactive_profiles.py
git diff database/repositories/profile_repo.py
git diff database/repositories/user_repo.py
git diff loader.py
git diff tasks/__init__.py
git diff keyboards/inline/admin_keyboard.py
git diff handlers/admin/admin_commands.py
```

---

## 2. Подготовка изменений локально

### 1.1 Проверка текущего состояния

```bash
# Перейдите в директорию проекта
cd ~/PycharmProjects/GO_Acquaintances_Bot

# Проверьте статус изменений
git status

# Посмотрите, какие файлы изменены
git diff
```

### 1.2 Добавление изменений в staging

```bash
# Добавьте все измененные файлы
git add .

# Или добавьте конкретные файлы
git add path/to/file1.py path/to/file2.py
```

### 1.3 Создание коммита

```bash
# Создайте коммит с описанием изменений
git commit -m "Описание изменений: что было добавлено/изменено"

# Примеры:
# git commit -m "Добавлена функция автоматической заморозки неактивных анкет"
# git commit -m "Добавлена функция бэкапа базы данных в админ-панель"
# git commit -m "Исправлена ошибка в обработке лайков"
```

---

## 3. Отправка изменений в GitHub

### 2.1 Отправка в удаленный репозиторий

```bash
# Отправьте изменения в GitHub
git push origin main

# Если используете другую ветку (например, master):
# git push origin master

# Если это первый push и нужно установить upstream:
# git push -u origin main
```

### 2.2 Проверка на GitHub

1. Откройте ваш репозиторий на GitHub
2. Убедитесь, что коммит появился в истории
3. Проверьте, что все файлы обновлены корректно

---

## 4. Обновление на сервере

### 3.1 Подключение к серверу

```bash
# Подключитесь к серверу по SSH
ssh botuser@YOUR_SERVER_IP

# Или если используете root:
# ssh root@YOUR_SERVER_IP

# Замените YOUR_SERVER_IP на IP-адрес вашего сервера
```

### 3.2 Остановка сервисов

⚠️ **Важно:** Останавливаем сервисы перед обновлением, чтобы избежать ошибок.

```bash
# Остановите основной бот
sudo systemctl stop dating-bot.service

# Остановите бэкенд Mini App
sudo systemctl stop dating-bot-backend.service

# Проверьте, что сервисы остановлены
sudo systemctl status dating-bot.service --no-pager
sudo systemctl status dating-bot-backend.service --no-pager
```

Ожидаемый статус: `inactive (dead)`

### 3.3 Обновление кода

```bash
# Перейдите в директорию проекта
cd ~/GO_Acquaintances_Bot

# Сохраните текущие изменения (если есть локальные правки)
git stash

# Получите последние изменения с GitHub
git fetch origin

# Обновите код
git pull origin main

# Если используете другую ветку:
# git pull origin master
```

### 3.4 Если возникли конфликты

```bash
# Посмотрите статус
git status

# Если нужно отменить слияние:
# git merge --abort

# Или разрешите конфликты вручную
# Отредактируйте файлы с конфликтами, затем:
git add .
git commit -m "Разрешение конфликтов"
```

### 3.5 Обновление зависимостей (если нужно)

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Обновите зависимости (если requirements.txt изменился)
pip install -r requirements.txt

# Обновите зависимости бэкенда (если нужно)
pip install -r admin_panel/mini_app/backend/requirements.txt

# Выйдите из виртуального окружения
deactivate
```

### 3.6 Пересборка фронтенда (если изменился)

```bash
# Перейдите в директорию фронтенда
cd ~/GO_Acquaintances_Bot/admin_panel/mini_app/frontend

# Установите зависимости (если package.json изменился)
npm install

# Пересоберите фронтенд
npm run build

# Вернитесь в корень проекта
cd ~/GO_Acquaintances_Bot
```

### 3.7 Запуск сервисов

```bash
# Запустите бэкенд первым
sudo systemctl start dating-bot-backend.service

# Запустите основной бот
sudo systemctl start dating-bot.service

# Проверьте статус
sudo systemctl status dating-bot.service --no-pager
sudo systemctl status dating-bot-backend.service --no-pager
```

**Ожидаемый статус:** `active (running)`

---

## 5. Изменение OWNER_TELEGRAM_ID

### 4.1 Что такое OWNER_TELEGRAM_ID?

`OWNER_TELEGRAM_ID` - это Telegram ID первого владельца (owner) бота. Этот пользователь автоматически получает права owner при первом запуске бота, если owner еще не существует в базе данных.

### 4.2 Как изменить OWNER_TELEGRAM_ID

#### На локальной машине:

```bash
# Перейдите в директорию проекта
cd ~/PycharmProjects/GO_Acquaintances_Bot

# Откройте файл .env в редакторе
nano .env
# или
vim .env
# или откройте в вашем IDE

# Найдите строку OWNER_TELEGRAM_ID и измените значение
OWNER_TELEGRAM_ID=123456789

# Сохраните файл
```

#### На сервере:

```bash
# Подключитесь к серверу
ssh botuser@YOUR_SERVER_IP

# Перейдите в директорию проекта
cd ~/GO_Acquaintances_Bot

# Откройте файл .env
nano .env
# или
vim .env

# Найдите строку OWNER_TELEGRAM_ID и измените значение
OWNER_TELEGRAM_ID=123456789

# Сохраните файл (в nano: Ctrl+O, Enter, Ctrl+X)
# В vim: нажмите i для редактирования, измените, Esc, :wq для сохранения
```

### 4.3 Создание нового owner

**Вопрос:** Создастся ли новый owner автоматически?

**Ответ:** Да, но с важными условиями:

1. **Автоматическое создание происходит только если:**
   - В базе данных еще нет ни одного owner (роль OWNER)
   - Указан валидный `OWNER_TELEGRAM_ID` в `.env`
   - Бот запускается после изменения `.env`

2. **Если owner уже существует:**
   - Новый owner **НЕ** создастся автоматически
   - Старый owner останется в базе данных
   - Чтобы назначить нового owner, нужно:
     - Либо удалить старого owner вручную через админ-панель
     - Либо изменить роль старого owner на другую (admin, moderator и т.д.)
     - Затем перезапустить бота

### 4.4 Процесс создания нового owner

```bash
# 1. Остановите бота
sudo systemctl stop dating-bot.service

# 2. Измените OWNER_TELEGRAM_ID в .env (см. выше)

# 3. Если нужно удалить старого owner (опционально):
# Подключитесь к базе данных
sqlite3 ~/GO_Acquaintances_Bot/dating_bot.db

# Посмотрите текущих owner
SELECT u.telegram_id, au.role 
FROM admin_users au 
JOIN users u ON au.user_id = u.id 
WHERE au.role = 'owner';

# Удалите старого owner (если нужно)
DELETE FROM admin_users WHERE role = 'owner';

# Выйдите из SQLite
.quit

# 4. Запустите бота
sudo systemctl start dating-bot.service

# 5. Проверьте логи
sudo journalctl -u dating-bot.service -n 50 --no-pager

# Должно появиться сообщение:
# "✅ Owner успешно инициализирован: telegram_id=YOUR_NEW_ID"
```

### 4.5 Проверка создания owner

```bash
# Проверьте логи бота
sudo journalctl -u dating-bot.service -n 100 | grep -i owner

# Или подключитесь к базе данных
sqlite3 ~/GO_Acquaintances_Bot/dating_bot.db

# Проверьте owner
SELECT u.telegram_id, u.username, au.role 
FROM admin_users au 
JOIN users u ON au.user_id = u.id 
WHERE au.role = 'owner';

# Выйдите
.quit
```

---

## 6. Проверка после обновления

### 5.1 Проверка логов

```bash
# Проверьте логи основного бота
sudo journalctl -u dating-bot.service -n 50 --no-pager

# Проверьте логи бэкенда
sudo journalctl -u dating-bot-backend.service -n 50 --no-pager

# Если есть ошибки, проверьте подробнее
sudo journalctl -u dating-bot.service -f
```

**Что искать в логах:**
- ✅ Нет ошибок при запуске
- ✅ Бот успешно подключился к Telegram
- ✅ Нет ошибок импорта модулей
- ✅ Планировщик задач запущен
- ✅ База данных подключена

### 5.2 Тестирование функционала

1. **Откройте Telegram бота**
2. **Проверьте основные функции:**
   - Команда `/start` работает
   - Просмотр анкет работает
   - Лайки работают
   - Админ-панель доступна (команда `/admin`)

3. **Проверьте новые функции:**
   - Если добавили новую функцию, протестируйте ее
   - Проверьте, что изменения работают корректно

### 5.3 Мониторинг (опционально)

```bash
# Следите за логами основного бота в реальном времени
sudo journalctl -u dating-bot.service -f

# В другом терминале следите за логами бэкенда
sudo journalctl -u dating-bot-backend.service -f
```

---

## 7. Решение проблем

### 6.1 Сервис не запускается

```bash
# Проверьте логи на наличие ошибок
sudo journalctl -u dating-bot.service -n 100

# Попробуйте запустить вручную для отладки
cd ~/GO_Acquaintances_Bot
source venv/bin/activate
python3.11 main.py
```

### 6.2 Конфликты при git pull

```bash
# Отмените слияние
git merge --abort

# Вернитесь к предыдущей версии
git reset --hard HEAD

# Попробуйте снова
git pull origin main
```

### 6.3 Нужно откатить изменения

```bash
# Остановите сервисы
sudo systemctl stop dating-bot.service
sudo systemctl stop dating-bot-backend.service

# Вернитесь к предыдущему коммиту
cd ~/GO_Acquaintances_Bot
git log --oneline -5  # посмотрите историю
git reset --hard HEAD~1  # вернитесь на один коммит назад

# Или вернитесь к конкретному коммиту
# git reset --hard COMMIT_HASH

# Запустите сервисы
sudo systemctl start dating-bot-backend.service
sudo systemctl start dating-bot.service
```

### 6.4 Ошибки импорта модулей

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Переустановите зависимости
pip install -r requirements.txt

# Проверьте, что все модули установлены
python3.11 -c "import aiogram; print('OK')"
```

### 6.5 Проблемы с базой данных

```bash
# Проверьте права доступа
ls -la ~/GO_Acquaintances_Bot/dating_bot.db

# Исправление прав
chmod 644 ~/GO_Acquaintances_Bot/dating_bot.db
chown botuser:botuser ~/GO_Acquaintances_Bot/dating_bot.db

# Проверка целостности БД
sqlite3 ~/GO_Acquaintances_Bot/dating_bot.db "PRAGMA integrity_check;"
```

---

## 📝 Краткая версия (для быстрого обновления)

Если вы уже знаете процесс, вот краткая версия:

```bash
# На локальной машине
cd ~/PycharmProjects/GO_Acquaintances_Bot
git add .
git commit -m "Описание изменений"
git push origin main

# На сервере
ssh botuser@YOUR_SERVER_IP
sudo systemctl stop dating-bot.service dating-bot-backend.service
cd ~/GO_Acquaintances_Bot && git pull origin main
source venv/bin/activate && pip install -r requirements.txt && deactivate
sudo systemctl start dating-bot-backend.service dating-bot.service
sudo systemctl status dating-bot.service dating-bot-backend.service
```

---

## ✅ Чеклист обновления

- [ ] Изменения закоммичены локально
- [ ] Изменения отправлены в GitHub
- [ ] Подключился к серверу
- [ ] Остановил сервисы
- [ ] Обновил код через `git pull`
- [ ] Обновил зависимости (если нужно)
- [ ] Пересобрал фронтенд (если нужно)
- [ ] Запустил сервисы
- [ ] Проверил статус сервисов (оба `active`)
- [ ] Проверил логи (нет ошибок)
- [ ] Протестировал функционал в боте
- [ ] Все работает корректно

---

**Готово! 🎉** Проект успешно обновлен.
