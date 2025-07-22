#!/usr/bin/env python3
"""
Скрипт для тестирования подключения к внешней базе данных
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к приложению
sys.path.append(str(Path(__file__).parent.parent))

from app.core.external_database import (
    check_external_db_connection,
    get_external_db_info,
    run_migrations_external_db,
)
from app.core.config import settings


async def main():
    """Основная функция тестирования"""

    print("🔍 Тестирование подключения к внешней базе данных")
    print("=" * 60)

    # Проверка переменных окружения
    print("📋 Проверка конфигурации:")
    print(f"   Host: {settings.POSTGRESQL_HOST}")
    print(f"   Port: {settings.POSTGRESQL_PORT}")
    print(f"   Database: {settings.POSTGRESQL_DBNAME}")
    print(f"   User: {settings.POSTGRESQL_USER}")
    print(f"   SSL Mode: {os.getenv('DB_SSL_MODE', 'prefer')}")
    print()

    # Тест подключения
    print("🔗 Тестирование подключения...")
    connection_ok = await check_external_db_connection()

    if not connection_ok:
        print("❌ Не удалось подключиться к базе данных!")
        print("\nПроверьте:")
        print("1. Правильность данных подключения")
        print("2. Доступность сервера БД")
        print("3. Настройки файрвола")
        print("4. SSL конфигурацию")
        return False

    # Получение информации о БД
    print("\n📊 Информация о базе данных:")
    db_info = await get_external_db_info()

    if db_info:
        print(f"   Версия PostgreSQL: {db_info['version'].split(',')[0]}")
        print(f"   Размер БД: {db_info['database_size']}")
        print(f"   Активные подключения: {db_info['active_connections']}")
        print(f"   Хост: {db_info['host']}:{db_info['port']}")

    # Проверка наличия таблиц
    print("\n🗂️  Проверка структуры БД...")
    try:
        from app.core.external_database import create_external_db_engine

        engine = create_external_db_engine()
        async with engine.begin() as conn:
            # Проверка наличия основных таблиц
            tables_result = await conn.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            )

            tables = [row[0] for row in tables_result.fetchall()]

            if tables:
                print(f"   Найдено таблиц: {len(tables)}")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("   ⚠️  Таблицы не найдены - возможно нужно применить миграции")

        await engine.dispose()

    except Exception as e:
        print(f"   ❌ Ошибка проверки структуры: {e}")

    # Проверка миграций
    print("\n🔄 Проверка состояния миграций...")
    try:
        from app.core.external_database import create_external_db_engine

        engine = create_external_db_engine()
        async with engine.begin() as conn:
            # Проверка таблицы alembic_version
            version_result = await conn.execute(
                """
                SELECT version_num 
                FROM alembic_version 
                LIMIT 1
            """
            )

            current_version = version_result.fetchone()
            if current_version:
                print(f"   Текущая версия миграции: {current_version[0]}")
            else:
                print("   ⚠️  Таблица alembic_version не найдена")

        await engine.dispose()

    except Exception as e:
        print(f"   ⚠️  Миграции еще не применены: {e}")

    print("\n✅ Тестирование завершено успешно!")
    return True


def test_env_vars():
    """Проверка обязательных переменных окружения"""
    required_vars = [
        "POSTGRESQL_HOST",
        "POSTGRESQL_PORT",
        "POSTGRESQL_USER",
        "POSTGRESQL_PASSWORD",
        "POSTGRESQL_DBNAME",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Отсутствуют обязательные переменные окружения:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nСоздайте .env файл или установите переменные!")
        return False

    return True


if __name__ == "__main__":
    # Загрузка .env файла если существует
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    # Проверка переменных
    if not test_env_vars():
        sys.exit(1)

    # Запуск тестирования
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)
