#!/bin/bash
# Скрипт для одновременного запуска бэкенда и фронтенда

cd "$(dirname "$0")"

echo "🚀 Запуск админ-панели (бэкенд + фронтенд)"
echo ""

# Функция для остановки всех процессов при выходе
cleanup() {
    echo ""
    echo "🛑 Остановка серверов..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Запуск бэкенда
echo "🔧 Запуск бэкенда на http://localhost:8000"
cd backend
python3 run.py &
BACKEND_PID=$!
cd ..

# Ждем немного, чтобы бэкенд успел запуститься
sleep 2

# Запуск фронтенда
echo "🌐 Запуск фронтенда на http://localhost:3000"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Оба сервера запущены!"
echo "📊 Бэкенд: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "🌐 Фронтенд: http://localhost:3000"
echo ""
echo "Нажмите Ctrl+C для остановки"

# Ждем завершения
wait
