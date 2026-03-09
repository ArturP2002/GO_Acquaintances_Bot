#!/usr/bin/env python3
"""
Скрипт для запуска бэкенда админ-панели в режиме разработки.
"""
import sys
import os
import uvicorn

# Добавляем корневую директорию проекта в путь
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    # Запуск сервера с автоперезагрузкой для разработки
    uvicorn.run(
        "admin_panel.mini_app.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[
            os.path.join(project_root, "admin_panel/mini_app/backend"),
            os.path.join(project_root, "database"),
            os.path.join(project_root, "core"),
        ],
        log_level="info"
    )
