#!/usr/bin/env python3
"""
Скрипт для запуска бэкенда и фронтенда mini app.
Используется для автоматического запуска вместе с ботом.
"""
import subprocess
import sys
import os
import signal
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Пути к директориям
project_root = Path(__file__).parent.parent.parent
backend_dir = project_root / "admin_panel" / "mini_app" / "backend"
frontend_dir = project_root / "admin_panel" / "mini_app" / "frontend"

# Глобальные переменные для процессов
backend_process = None
frontend_process = None


def start_backend():
    """Запускает бэкенд FastAPI."""
    global backend_process
    
    try:
        logger.info("Запуск бэкенда mini app...")
        
        # Запускаем бэкенд через uvicorn
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "admin_panel.mini_app.backend.main:app", 
             "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Бэкенд запущен (PID: {backend_process.pid}) на http://localhost:8000")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бэкенда: {e}", exc_info=True)
        return False


def start_frontend():
    """Запускает фронтенд Vite."""
    global frontend_process
    
    try:
        logger.info("Запуск фронтенда mini app...")
        
        # Проверяем наличие node_modules
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            logger.warning("node_modules не найден. Установите зависимости: cd admin_panel/mini_app/frontend && npm install")
            return False
        
        # Запускаем фронтенд через npm
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Фронтенд запущен (PID: {frontend_process.pid}) на http://localhost:3000")
        return True
        
    except FileNotFoundError:
        logger.error("npm не найден. Убедитесь, что Node.js установлен.")
        return False
    except Exception as e:
        logger.error(f"Ошибка при запуске фронтенда: {e}", exc_info=True)
        return False


def stop_servers():
    """Останавливает оба сервера."""
    global backend_process, frontend_process
    
    logger.info("Остановка серверов mini app...")
    
    if backend_process:
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
            logger.info("Бэкенд остановлен")
        except subprocess.TimeoutExpired:
            backend_process.kill()
            logger.warning("Бэкенд принудительно остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бэкенда: {e}")
    
    if frontend_process:
        try:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
            logger.info("Фронтенд остановлен")
        except subprocess.TimeoutExpired:
            frontend_process.kill()
            logger.warning("Фронтенд принудительно остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке фронтенда: {e}")


def start_all():
    """Запускает оба сервера."""
    backend_ok = start_backend()
    frontend_ok = start_frontend()
    
    if backend_ok and frontend_ok:
        logger.info("✅ Mini App серверы успешно запущены")
        return True
    else:
        logger.warning("⚠️ Не все серверы запущены успешно")
        return False


# Обработчик сигналов для корректного завершения
def signal_handler(signum, frame):
    """Обработчик сигналов для остановки серверов."""
    stop_servers()
    sys.exit(0)


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запуск серверов
    if start_all():
        try:
            # Ждем завершения процессов
            if backend_process:
                backend_process.wait()
            if frontend_process:
                frontend_process.wait()
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        finally:
            stop_servers()
    else:
        sys.exit(1)
