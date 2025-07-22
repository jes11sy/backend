#!/usr/bin/env python3
"""
Скрипт для запуска приложения в режиме разработки
БЕЗ логирования в файл (только в консоль)
"""
import os
import uvicorn
from uvicorn_config import UVICORN_CONFIG

# Отключаем логирование в файл для разработки
os.environ["LOG_TO_FILE"] = "false"
os.environ["ENVIRONMENT"] = "development"

# Модифицируем конфигурацию для разработки
dev_config = UVICORN_CONFIG.copy()
dev_config.update(
    {
        "log_level": "info",
        "access_log": False,  # Отключаем access log
        "reload_delay": 0.25,  # Задержка перед перезагрузкой
    }
)

if __name__ == "__main__":
    print("🚀 Запуск сервера разработки (БЕЗ логов в файл)...")
    print("📁 Отслеживаемые директории:", dev_config["reload_dirs"])
    print("🚫 Игнорируемые паттерны:", dev_config["reload_excludes"][:8], "...")
    print("📝 Логи только в консоль")

    uvicorn.run("app.main:app", **dev_config)
