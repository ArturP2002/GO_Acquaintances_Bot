# 🚀 Локальный запуск Mini App

Инструкция по запуску админ-панели (Mini App) для локального тестирования.

## 📋 Требования

### Для бэкенда:
- Python 3.8+
- pip
- Виртуальное окружение (рекомендуется)

### Для фронтенда:
- Node.js 18+
- npm или yarn

---

## 🔧 Шаг 1: Установка зависимостей

### Бэкенд

1. Перейдите в директорию бэкенда:
```bash
cd admin_panel/mini_app/backend
```

2. Установите зависимости:
```bash
pip3 install -r requirements.txt
```

**Или из корня проекта:**
```bash
pip3 install -r admin_panel/mini_app/backend/requirements.txt
```

**Примечание для macOS:** Используйте `pip3` и `python3` вместо `pip` и `python`.

### Фронтенд

1. Перейдите в директорию фронтенда:
```bash
cd admin_panel/mini_app/frontend
```

2. Установите зависимости:
```bash
npm install
```

---

## 🚀 Шаг 2: Запуск серверов

### Вариант 1: Запуск по отдельности (рекомендуется для разработки)

#### Запуск бэкенда:

**Способ 1: Через скрипт (рекомендуется)**
```bash
cd admin_panel/mini_app/backend
python3 run.py
```

**Способ 2: Через uvicorn напрямую**
```bash
cd admin_panel/mini_app/backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Способ 3: Из корня проекта**
```bash
python3 -m uvicorn admin_panel.mini_app.backend.main:app --reload --host 0.0.0.0 --port 8000
```

Бэкенд будет доступен по адресу: **http://localhost:8000**

API документация:
- Swagger UI: **http://localhost:8000/docs**
- ReDoc: **http://localhost:8000/redoc**

#### Запуск фронтенда:

**Способ 1: Через скрипт (Linux/Mac)**
```bash
cd admin_panel/mini_app/frontend
chmod +x start-dev.sh
./start-dev.sh
```

**Способ 2: Через скрипт (Windows)**
```bash
cd admin_panel/mini_app/frontend
start-dev.bat
```

**Способ 3: Через npm напрямую**
```bash
cd admin_panel/mini_app/frontend
npm run dev
```

Фронтенд будет доступен по адресу: **http://localhost:3000**

### Вариант 2: Запуск всего вместе (одной командой)

**Linux/Mac:**
```bash
cd admin_panel/mini_app
chmod +x start-all.sh
./start-all.sh
```

**Windows:**
Используйте два отдельных терминала для бэкенда и фронтенда.

---

## 🔗 Шаг 3: Настройка Telegram Bot для локального тестирования

### Вариант A: Использование ngrok (для тестирования в Telegram)

1. **Установите ngrok:**
   - **macOS (рекомендуется):** `brew install ngrok/ngrok/ngrok`
   - Или скачайте с https://ngrok.com

2. **Запустите ngrok для фронтенда:**
```bash
ngrok http 3000
```

3. **Скопируйте HTTPS URL** (например: `https://abc123.ngrok.io`)

4. **Настройте бэкенд для работы с ngrok:**
   - В файле `admin_panel/mini_app/backend/main.py` временно измените CORS:
   ```python
   allow_origins=["https://abc123.ngrok.io", "http://localhost:3000"]
   ```

5. **Настройте BotFather:**
   - Откройте [@BotFather](https://t.me/BotFather)
   - `/mybots` → выберите вашего бота
   - Bot Settings → Menu Button
   - Введите URL: `https://abc123.ngrok.io`

### Вариант B: Локальное тестирование без Telegram

1. Откройте **http://localhost:3000** в браузере
2. Для тестирования API используйте Swagger UI: **http://localhost:8000/docs**
3. Для авторизации вручную установите токен в localStorage:
   ```javascript
   localStorage.setItem('auth_token', 'ваш_telegram_id')
   ```

---

## 🧪 Тестирование

### 1. Проверка бэкенда

Откройте в браузере:
- **http://localhost:8000** - должен вернуть `{"message": "Admin Panel API", "status": "running"}`
- **http://localhost:8000/health** - должен вернуть `{"status": "healthy"}`
- **http://localhost:8000/docs** - Swagger UI с документацией API

### 2. Проверка фронтенда

Откройте в браузере:
- **http://localhost:3000** - должен открыться интерфейс админ-панели

### 3. Проверка связи фронтенд ↔ бэкенд

1. Откройте консоль браузера (F12)
2. Перейдите на любую страницу админ-панели
3. Проверьте, что нет ошибок CORS
4. Проверьте Network tab - запросы должны идти на `http://localhost:8000`

---

## ⚙️ Настройка переменных окружения (опционально)

### Фронтенд

Создайте файл `.env` в `admin_panel/mini_app/frontend/`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

По умолчанию используется `http://localhost:8000`, так что это необязательно.

### Бэкенд

Бэкенд использует те же переменные окружения, что и основной бот (из `.env` в корне проекта).

---

## 🐛 Решение проблем

### Проблема: "Module not found" при запуске бэкенда

**Решение:**
```bash
# Убедитесь, что вы в корне проекта или установите зависимости глобально
# Для macOS используйте pip3
pip3 install -r admin_panel/mini_app/backend/requirements.txt
```

### Проблема: "CORS error" в консоли браузера

**Решение:**
- Убедитесь, что бэкенд запущен на порту 8000
- Проверьте, что CORS настроен правильно (по умолчанию разрешены все домены для разработки)

### Проблема: Фронтенд не подключается к бэкенду

**Решение:**
1. Проверьте, что бэкенд запущен: откройте http://localhost:8000/docs
2. Проверьте переменную `VITE_API_BASE_URL` в `.env` файле фронтенда
3. Проверьте консоль браузера на наличие ошибок

### Проблема: "Port 3000 already in use"

**Решение:**
```bash
# Найдите процесс, использующий порт 3000
lsof -ti:3000 | xargs kill -9  # Mac/Linux
# или
netstat -ano | findstr :3000  # Windows, затем taskkill /PID <pid> /F
```

### Проблема: "Port 8000 already in use"

**Решение:**
```bash
# Найдите процесс, использующий порт 8000
lsof -ti:8000 | xargs kill -9  # Mac/Linux
# или
netstat -ano | findstr :8000  # Windows, затем taskkill /PID <pid> /F
```

---

## 📝 Полезные команды

### Бэкенд

```bash
# Запуск с автоперезагрузкой
python3 run.py

# Запуск без автоперезагрузки
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# Запуск с другим портом
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080
```

### Фронтенд

```bash
# Запуск dev-сервера
npm run dev

# Сборка для продакшена
npm run build

# Просмотр собранной версии
npm run preview

# Проверка кода
npm run lint
```

---

## 🔐 Авторизация для тестирования

Для локального тестирования без Telegram:

1. Откройте консоль браузера (F12)
2. Выполните:
```javascript
// Установите токен (telegram_id пользователя-администратора)
localStorage.setItem('auth_token', '123456789')  // Замените на реальный telegram_id

// Обновите страницу
location.reload()
```

**Важно:** В продакшене авторизация будет происходить через Telegram Mini App автоматически.

---

## 📚 Дополнительная информация

- **API документация:** http://localhost:8000/docs
- **Backend README:** `admin_panel/mini_app/backend/README.md`
- **Frontend README:** `admin_panel/mini_app/frontend/README.md`

---

## ✅ Чеклист для запуска

- [ ] Установлены зависимости бэкенда (`pip install -r requirements.txt`)
- [ ] Установлены зависимости фронтенда (`npm install`)
- [ ] Бэкенд запущен на http://localhost:8000
- [ ] Фронтенд запущен на http://localhost:3000
- [ ] Нет ошибок в консоли браузера
- [ ] API запросы работают (проверено в Network tab)

Удачи с тестированием! 🚀
