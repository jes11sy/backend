#!/usr/bin/env python3
"""
Минимальный запуск для разработки
- Без логирования в файл
- Без мониторинга
- Только отслеживание app/ директории
"""
import os
import uvicorn

# Отключаем все что может вызывать изменения файлов
os.environ["LOG_TO_FILE"] = "false"
os.environ["ENVIRONMENT"] = "development"
os.environ["ENABLE_MONITORING"] = "false"

# Минимальная конфигурация uvicorn
MINIMAL_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": True,
    "reload_dirs": ["app"],  # Только app директория
    "reload_excludes": [
        "*.log*",
        "*.tmp*", 
        "media/*",
        "__pycache__/*",
        "*.pyc",
        "*.pyo",
        "venv/*",
        "env/*",
        ".env*",
        ".git/*",
        "docs/*",
        "frontend/*",
        "backup/*",
        "*.md",
        "*.txt",
        "*.sqlite*",
        "*.db*",
        "alembic/versions/*",
        "logs/*"
    ],
    "log_level": "info",
    "access_log": False,
    "reload_delay": 0.5,
}

if __name__ == "__main__":
    print("🚀 МИНИМАЛЬНЫЙ запуск для разработки")
    print("❌ Логи в файл: ОТКЛЮЧЕНЫ")
    print("❌ Мониторинг: ОТКЛЮЧЕН")
    print("📁 Отслеживание: ТОЛЬКО app/")
    print("🔄 Перезагрузка: задержка 0.5с")
    print()
    
    uvicorn.run(
        "app.main:app",
        **MINIMAL_CONFIG
    ) 