# 🚀 Инструкция по развертыванию бота на VPS сервере (Timeweb Cloud)

Подробная инструкция по размещению Telegram-бота знакомств на VPS сервере Timeweb Cloud.

---

## 📋 Содержание

1. [Подготовка VPS сервера](#1-подготовка-vps-сервера)
2. [Установка зависимостей](#2-установка-зависимостей)
3. [Настройка проекта](#3-настройка-проекта)
4. [Настройка systemd сервисов](#4-настройка-systemd-сервисов)
5. [Настройка Nginx для Mini App](#5-настройка-nginx-для-mini-app)
6. [Настройка SSL сертификатов](#6-настройка-ssl-сертификатов)
7. [Запуск и проверка](#7-запуск-и-проверка)
8. [Мониторинг и логирование](#8-мониторинг-и-логирование)
9. [Обновление бота](#9-обновление-бота)
10. [Решение проблем](#10-решение-проблем)

---

## 1. Подготовка VPS сервера

### 1.1 Создание VPS в Timeweb Cloud

1. Войдите в панель управления [Timeweb Cloud](https://timeweb.cloud/)
2. Создайте новый VPS:
   - **ОС**: Ubuntu 22.04 LTS (рекомендуется)
   - **RAM**: минимум 2 GB (рекомендуется 4 GB)
   - **CPU**: минимум 2 ядра
   - **Диск**: минимум 20 GB SSD
3. Запишите IP-адрес сервера
4. Создайте SSH ключ или используйте пароль для доступа

### 1.2 Подключение к серверу

```bash
# Подключение по SSH
ssh root@YOUR_SERVER_IP

# Или с использованием ключа
ssh -i ~/.ssh/your_key root@YOUR_SERVER_IP
```

### 1.3 Обновление системы

```bash
# Обновление списка пакетов
apt update && apt upgrade -y

# Установка базовых утилит
apt install -y curl wget git build-essential software-properties-common
```

### 1.4 Создание пользователя для бота (опционально, но рекомендуется)

```bash
# Создание пользователя
adduser botuser
usermod -aG sudo botuser

# Переключение на нового пользователя
su - botuser
```

---

## 2. Установка зависимостей

### 2.1 Установка Python 3.11+

```bash
# Добавление репозитория deadsnakes для Python 3.11
add-apt-repository ppa:deadsnakes/ppa -y
apt update

# Установка Python 3.11 и необходимых пакетов
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Проверка версии
python3.11 --version
```

### 2.2 Установка Node.js и npm (для Mini App фронтенда)

```bash
# Установка Node.js 18.x через NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Проверка версий
node --version
npm --version
```

### 2.3 Установка Nginx

```bash
# Установка Nginx
apt install -y nginx

# Запуск и автозапуск
systemctl start nginx
systemctl enable nginx

# Проверка статуса
systemctl status nginx
```

### 2.4 Установка Certbot (для SSL сертификатов)

```bash
# Установка Certbot
apt install -y certbot python3-certbot-nginx
```

---

## 3. Настройка проекта

### 3.1 Клонирование проекта

```bash
# Переход в домашнюю директорию
cd ~

# Клонирование репозитория (замените на ваш репозиторий)
git clone https://github.com/ArturP2002/GO_Acquaintances_Bot.git

git clone https://github.com/your-username/GO_Acquaintances_Bot.git
# Или загрузите проект через scp/sftp

cd GO_Acquaintances_Bot
```

### 3.2 Создание виртуального окружения Python

```bash
# Создание виртуального окружения
python3.11 -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Обновление pip
pip install --upgrade pip
```

### 3.3 Установка зависимостей Python

```bash
# Установка зависимостей основного бота
pip install -r requirements.txt

# Установка зависимостей бэкенда Mini App
pip install -r admin_panel/mini_app/backend/requirements.txt
```

### 3.4 Установка зависимостей Node.js (для фронтенда)

```bash
# Переход в директорию фронтенда
cd admin_panel/mini_app/frontend

# Установка зависимостей
npm install

# Сборка фронтенда для продакшена
npm run build

# Возврат в корень проекта
cd ~/GO_Acquaintances_Bot
```

### 3.5 Настройка переменных окружения

```bash
# Создание файла .env
nano .env
```

Добавьте следующие переменные (замените значения на ваши):

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
DATABASE_PATH=/home/botuser/GO_Acquaintances_Bot/dating_bot.db

# Логирование
LOG_LEVEL=INFO
LOG_FILE=/home/botuser/GO_Acquaintances_Bot/bot.log

# Инициализация owner
OWNER_TELEGRAM_ID=your_telegram_id

# Mini App (будет настроено после настройки домена)
MINI_APP_URL=https://your-domain.com
```

**Важно**: Замените `botuser` на ваше имя пользователя, если создавали отдельного пользователя.

### 3.6 Настройка переменных окружения для фронтенда

```bash
# Создание .env файла для фронтенда
nano admin_panel/mini_app/frontend/.env
```

Добавьте:

```env
VITE_API_BASE_URL=https://your-domain.com/api
```

---

## 4. Настройка systemd сервисов

### 4.1 Создание сервиса для основного бота

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/dating-bot.service
```

Добавьте следующее содержимое (замените `botuser` на ваше имя пользователя):

```ini
[Unit]
Description=Telegram Dating Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/GO_Acquaintances_Bot
Environment="PATH=/home/botuser/GO_Acquaintances_Bot/venv/bin"
ExecStart=/home/botuser/GO_Acquaintances_Bot/venv/bin/python3.11 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4.2 Создание сервиса для бэкенда Mini App

```bash
sudo nano /etc/systemd/system/dating-bot-backend.service
```

```ini
[Unit]
Description=Dating Bot Mini App Backend
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/GO_Acquaintances_Bot
Environment="PATH=/home/botuser/GO_Acquaintances_Bot/venv/bin"
ExecStart=/home/botuser/GO_Acquaintances_Bot/venv/bin/uvicorn admin_panel.mini_app.backend.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4.3 Активация и запуск сервисов

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable dating-bot.service
sudo systemctl enable dating-bot-backend.service

# Запуск сервисов
sudo systemctl start dating-bot.service
sudo systemctl start dating-bot-backend.service

# Проверка статуса
sudo systemctl status dating-bot.service
sudo systemctl status dating-bot-backend.service
```

---

## 5. Настройка Nginx для Mini App

### 5.1 Настройка домена

1. В панели Timeweb Cloud добавьте домен и укажите A-запись на IP вашего сервера
2. Дождитесь распространения DNS (обычно 5-30 минут)

### 5.2 Создание конфигурации Nginx

```bash
# Создание конфигурации
sudo nano /etc/nginx/sites-available/dating-bot
```

Добавьте следующую конфигурацию (замените `your-domain.com` на ваш домен):

```nginx
# Редирект с HTTP на HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS конфигурация
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL сертификаты (будут настроены через Certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Максимальный размер загружаемых файлов
    client_max_body_size 10M;

    # Проксирование API запросов к бэкенду
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Раздача статических файлов фронтенда
    location / {
        root /home/botuser/GO_Acquaintances_Bot/admin_panel/mini_app/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # Кэширование статических файлов
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Логирование
    access_log /var/log/nginx/dating-bot-access.log;
    error_log /var/log/nginx/dating-bot-error.log;
}
```

### 5.3 Активация конфигурации

```bash
# Создание символической ссылки
sudo ln -s /etc/nginx/sites-available/dating-bot /etc/nginx/sites-enabled/

# Удаление дефолтной конфигурации (опционально)
sudo rm /etc/nginx/sites-enabled/default

# Проверка конфигурации
sudo nginx -t

# Перезагрузка Nginx
sudo systemctl reload nginx
```

---

## 6. Настройка SSL сертификатов

### 6.1 Получение SSL сертификата через Certbot

```bash
# Получение сертификата (замените на ваш домен и email)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com --email your-email@example.com --agree-tos --non-interactive

sudo certbot --nginx -d goznakomstva.tw1.ru -d www.goznakomstva.tw1.ru --email aprorasov@gmail.com --agree-tos --non-interactive

# Автоматическое обновление сертификатов
sudo certbot renew --dry-run
```

### 6.2 Настройка автообновления сертификатов

Certbot автоматически создает cron-задачу для обновления сертификатов. Проверить можно командой:

```bash
sudo systemctl list-timers | grep certbot
```

---

## 7. Запуск и проверка

### 7.1 Обновление URL Mini App в конфигурации

```bash
# Редактирование .env файла
nano .env
```

Обновите `MINI_APP_URL`:

```env
MINI_APP_URL=https://your-domain.com
```

### 7.2 Перезапуск сервисов

```bash
# Перезапуск бота
sudo systemctl restart dating-bot.service

# Перезапуск бэкенда
sudo systemctl restart dating-bot-backend.service

# Проверка статуса
sudo systemctl status dating-bot.service
sudo systemctl status dating-bot-backend.service
```

### 7.3 Проверка работы

1. **Проверка бота:**
   ```bash
   # Просмотр логов
   sudo journalctl -u dating-bot.service -f
   ```

2. **Проверка бэкенда:**
   ```bash
   # Просмотр логов
   sudo journalctl -u dating-bot-backend.service -f
   
   # Проверка API
   curl http://localhost:8000/health
   ```

3. **Проверка фронтенда:**
   - Откройте в браузере: `https://your-domain.com`
   - Должен открыться интерфейс админ-панели

4. **Проверка Nginx:**
   ```bash
   sudo systemctl status nginx
   sudo tail -f /var/log/nginx/dating-bot-access.log
   ```

### 7.4 Настройка Mini App в BotFather

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/mybots`
3. Выберите вашего бота
4. Выберите "Bot Settings" → "Menu Button"
5. Введите URL: `https://your-domain.com`
6. Сохраните изменения

---

## 8. Мониторинг и логирование

### 8.1 Просмотр логов бота

```bash
# Логи через journalctl
sudo journalctl -u dating-bot.service -f

# Логи из файла (если настроен LOG_FILE)
tail -f ~/GO_Acquaintances_Bot/bot.log
```

### 8.2 Просмотр логов бэкенда

```bash
sudo journalctl -u dating-bot-backend.service -f
```

### 8.3 Мониторинг ресурсов

```bash
# Использование CPU и памяти
htop

# Использование диска
df -h

# Использование памяти процессами
ps aux --sort=-%mem | head
```

### 8.4 Настройка ротации логов (опционально)

```bash
# Создание конфигурации logrotate
sudo nano /etc/logrotate.d/dating-bot
```

Добавьте:

```
/home/botuser/GO_Acquaintances_Bot/bot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 botuser botuser
}
```

---

## 9. Обновление бота

### 9.1 Обновление кода

```bash
# Переход в директорию проекта
cd ~/GO_Acquaintances_Bot

# Остановка сервисов
sudo systemctl stop dating-bot.service
sudo systemctl stop dating-bot-backend.service

# Обновление кода (если используете git)
git pull origin main

# Или загрузите новые файлы через scp/sftp

# Обновление зависимостей (если изменились)
source venv/bin/activate
pip install -r requirements.txt
pip install -r admin_panel/mini_app/backend/requirements.txt

# Обновление фронтенда (если изменился)
cd admin_panel/mini_app/frontend
npm install
npm run build
cd ~/GO_Acquaintances_Bot

# Запуск сервисов
sudo systemctl start dating-bot-backend.service
sudo systemctl start dating-bot.service

# Проверка статуса
sudo systemctl status dating-bot.service
sudo systemctl status dating-bot-backend.service
```

### 9.2 Создание скрипта для обновления

```bash
# Создание скрипта
nano ~/update-bot.sh
```

Добавьте:

```bash
#!/bin/bash
cd ~/GO_Acquaintances_Bot

echo "Остановка сервисов..."
sudo systemctl stop dating-bot.service
sudo systemctl stop dating-bot-backend.service

echo "Обновление кода..."
git pull origin main

echo "Обновление зависимостей..."
source venv/bin/activate
pip install -r requirements.txt
pip install -r admin_panel/mini_app/backend/requirements.txt

echo "Обновление фронтенда..."
cd admin_panel/mini_app/frontend
npm install
npm run build
cd ~/GO_Acquaintances_Bot

echo "Запуск сервисов..."
sudo systemctl start dating-bot-backend.service
sudo systemctl start dating-bot.service

echo "Проверка статуса..."
sudo systemctl status dating-bot.service --no-pager
sudo systemctl status dating-bot-backend.service --no-pager

echo "Обновление завершено!"
```

Сделайте скрипт исполняемым:

```bash
chmod +x ~/update-bot.sh
```

### 9.3 Подробная инструкция по обновлению файлов через GitHub

#### Вариант 1: Обновление всего проекта

Если вы обновили код на GitHub и хотите загрузить все изменения на сервер:

```bash
# 1. Подключитесь к серверу по SSH
ssh botuser@YOUR_SERVER_IP

# 2. Перейдите в директорию проекта
cd ~/GO_Acquaintances_Bot

# 3. Остановите сервисы (чтобы избежать ошибок при обновлении)
sudo systemctl stop dating-bot.service
sudo systemctl stop dating-bot-backend.service

# 4. Сохраните текущие изменения (если есть локальные правки)
git stash

# 5. Получите последние изменения с GitHub
git fetch origin

# 6. Обновите код (замените main на вашу ветку, если используете другую)
git pull origin main

# 7. Если были конфликты, разрешите их вручную
# git status  # проверьте статус
# git merge --abort  # если нужно отменить слияние

# 8. Обновите зависимости Python (если изменились requirements.txt)
source venv/bin/activate
pip install -r requirements.txt
pip install -r admin_panel/mini_app/backend/requirements.txt

# 9. Обновите зависимости фронтенда (если изменился package.json)
cd admin_panel/mini_app/frontend
npm install
npm run build
cd ~/GO_Acquaintances_Bot

# 10. Запустите сервисы
sudo systemctl start dating-bot-backend.service
sudo systemctl start dating-bot.service

# 11. Проверьте статус
sudo systemctl status dating-bot.service --no-pager
sudo systemctl status dating-bot-backend.service --no-pager

# 12. Проверьте логи на наличие ошибок
sudo journalctl -u dating-bot.service -n 50
sudo journalctl -u dating-bot-backend.service -n 50
```

#### Вариант 2: Обновление конкретного файла

Если вы обновили только один файл на GitHub и хотите загрузить только его:

```bash
# 1. Подключитесь к серверу
ssh botuser@YOUR_SERVER_IP

# 2. Перейдите в директорию проекта
cd ~/GO_Acquaintances_Bot

# 3. Остановите сервисы
sudo systemctl stop dating-bot.service
sudo systemctl stop dating-bot-backend.service

# 4. Получите конкретный файл с GitHub
# Например, если обновили main.py:
git fetch origin
git checkout origin/main -- main.py

# Или для файла в поддиректории:
git checkout origin/main -- handlers/user/browse_profiles.py

# 5. Если обновили конфигурационные файлы, проверьте их
# Например, если обновили config.py:
# nano config.py  # проверьте настройки

# 6. Запустите сервисы
sudo systemctl start dating-bot-backend.service
sudo systemctl start dating-bot.service

# 7. Проверьте статус и логи
sudo systemctl status dating-bot.service --no-pager
```

#### Вариант 3: Принудительное обновление (перезапись локальных изменений)

⚠️ **Внимание**: Этот метод удалит все локальные изменения на сервере!

```bash
# 1. Подключитесь к серверу
ssh botuser@YOUR_SERVER_IP

# 2. Перейдите в директорию проекта
cd ~/GO_Acquaintances_Bot

# 3. Остановите сервисы
sudo systemctl stop dating-bot.service
sudo systemctl stop dating-bot-backend.service

# 4. Сохраните резервную копию (рекомендуется)
cp -r ~/GO_Acquaintances_Bot ~/GO_Acquaintances_Bot.backup

# 5. Сбросьте все локальные изменения и получите версию с GitHub
git fetch origin
git reset --hard origin/main

# 6. Обновите зависимости
source venv/bin/activate
pip install -r requirements.txt
pip install -r admin_panel/mini_app/backend/requirements.txt

cd admin_panel/mini_app/frontend
npm install
npm run build
cd ~/GO_Acquaintances_Bot

# 7. Восстановите файл .env (если он был перезаписан)
# Если .env был удален, создайте его заново:
# nano .env
# Добавьте необходимые переменные окружения

# 8. Запустите сервисы
sudo systemctl start dating-bot-backend.service
sudo systemctl start dating-bot.service

# 9. Проверьте статус
sudo systemctl status dating-bot.service --no-pager
```

#### Вариант 4: Обновление через веб-интерфейс GitHub (без SSH)

Если у вас нет прямого доступа к серверу, но есть доступ к GitHub:

1. **Обновите файлы на GitHub:**
   - Зайдите в репозиторий на GitHub
   - Отредактируйте нужные файлы через веб-интерфейс
   - Создайте коммит и push

2. **На сервере выполните:**
   ```bash
   # Через SSH или через панель управления сервером
   cd ~/GO_Acquaintances_Bot
   sudo systemctl stop dating-bot.service
   sudo systemctl stop dating-bot-backend.service
   git pull origin main
   sudo systemctl start dating-bot-backend.service
   sudo systemctl start dating-bot.service
   ```

#### Полезные команды Git для работы с обновлениями

```bash
# Проверить статус репозитория
git status

# Посмотреть последние коммиты
git log --oneline -10

# Посмотреть различия между локальной и удаленной версией
git diff origin/main

# Отменить локальные изменения в конкретном файле
git checkout -- filename.py

# Посмотреть, какие файлы изменились
git diff --name-only origin/main

# Создать резервную копию перед обновлением
git branch backup-$(date +%Y%m%d-%H%M%S)
```

#### Автоматическое обновление через cron (опционально)

Для автоматического обновления каждую ночь:

```bash
# Откройте crontab
crontab -e

# Добавьте строку (обновление в 3:00 ночи каждый день)
0 3 * * * cd ~/GO_Acquaintances_Bot && git pull origin main && sudo systemctl restart dating-bot.service dating-bot-backend.service
```

⚠️ **Рекомендации:**
- Всегда делайте резервную копию перед обновлением
- Проверяйте логи после обновления
- Тестируйте изменения на тестовом сервере перед применением на продакшене
- Сохраняйте файл `.env` отдельно, чтобы он не был перезаписан

---

## 10. Решение проблем

### 10.1 Бот не запускается

```bash
# Проверка логов
sudo journalctl -u dating-bot.service -n 50

# Проверка конфигурации
cd ~/GO_Acquaintances_Bot
source venv/bin/activate
python3.11 main.py
```

**Частые проблемы:**
- Неверный `BOT_TOKEN` → проверьте `.env` файл
- Отсутствие прав на файл БД → `chmod 644 dating_bot.db`
- Неверный путь к БД → проверьте `DATABASE_PATH` в `.env`

### 10.2 Бэкенд не отвечает

```bash
# Проверка логов
sudo journalctl -u dating-bot-backend.service -n 50

# Проверка порта
sudo netstat -tlnp | grep 8000

# Ручной запуск для отладки
cd ~/GO_Acquaintances_Bot
source venv/bin/activate
uvicorn admin_panel.mini_app.backend.main:app --host 127.0.0.1 --port 8000
```

### 10.3 Nginx не работает

```bash
# Проверка конфигурации
sudo nginx -t

# Проверка логов
sudo tail -f /var/log/nginx/error.log

# Проверка статуса
sudo systemctl status nginx
```

### 10.4 SSL сертификат не работает

```bash
# Проверка сертификата
sudo certbot certificates

# Обновление сертификата вручную
sudo certbot renew

# Проверка Nginx конфигурации
sudo nginx -t
```

### 10.5 Фронтенд не загружается

```bash
# Проверка сборки
ls -la ~/GO_Acquaintances_Bot/admin_panel/mini_app/frontend/dist

# Пересборка фронтенда
cd ~/GO_Acquaintances_Bot/admin_panel/mini_app/frontend
npm run build

# Проверка прав доступа
sudo chown -R botuser:botuser ~/GO_Acquaintances_Bot/admin_panel/mini_app/frontend/dist
```

### 10.6 Проблемы с базой данных

```bash
# Проверка прав доступа
ls -la ~/GO_Acquaintances_Bot/dating_bot.db

# Исправление прав
chmod 644 ~/GO_Acquaintances_Bot/dating_bot.db
chown botuser:botuser ~/GO_Acquaintances_Bot/dating_bot.db

# Проверка целостности БД
sqlite3 ~/GO_Acquaintances_Bot/dating_bot.db "PRAGMA integrity_check;"
```

---

## 📝 Дополнительные рекомендации

### Безопасность

1. **Настройка файрвола:**
   ```bash
   # Установка UFW
   sudo apt install ufw
   
   # Разрешение SSH, HTTP, HTTPS
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   
   # Включение файрвола
   sudo ufw enable
   ```

2. **Регулярные обновления:**
   ```bash
   # Настройка автоматических обновлений безопасности
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

3. **Резервное копирование:**
   - Настройте регулярное резервное копирование базы данных
   - Используйте cron для автоматических бэкапов

### Производительность

1. **Оптимизация Python:**
   - Используйте `uvloop` для улучшения производительности asyncio
   - Настройте пулы соединений для БД

2. **Кэширование:**
   - Используйте Redis для кэширования (опционально)
   - Настройте кэширование в Nginx

---

## ✅ Чеклист развертывания

- [ ] VPS сервер создан и настроен
- [ ] Python 3.11+ установлен
- [ ] Node.js 18+ установлен
- [ ] Nginx установлен и настроен
- [ ] Проект загружен на сервер
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] Фронтенд собран (`npm run build`)
- [ ] Файл `.env` создан и настроен
- [ ] Systemd сервисы созданы и запущены
- [ ] Домен настроен и указывает на сервер
- [ ] SSL сертификат получен и настроен
- [ ] Nginx конфигурация создана и активирована
- [ ] Бот запущен и работает
- [ ] Бэкенд запущен и отвечает
- [ ] Фронтенд доступен по HTTPS
- [ ] Mini App настроен в BotFather
- [ ] Логирование настроено
- [ ] Мониторинг настроен

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи сервисов
2. Проверьте конфигурацию Nginx
3. Проверьте переменные окружения
4. Убедитесь, что все порты открыты
5. Проверьте права доступа к файлам

---

**Удачи с развертыванием! 🚀**
