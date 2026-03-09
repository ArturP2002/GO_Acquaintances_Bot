@echo off
REM Скрипт для запуска фронтенда в режиме разработки (Windows)

cd /d "%~dp0"

echo 🚀 Запуск фронтенда админ-панели...
echo 📦 Проверка зависимостей...

REM Проверяем, установлены ли зависимости
if not exist "node_modules" (
    echo 📥 Установка зависимостей...
    call npm install
)

echo ✅ Зависимости установлены
echo 🌐 Запуск dev-сервера на http://localhost:3000
echo.

REM Запускаем dev-сервер
call npm run dev
