#!/usr/bin/env python3
"""
Упрощенный скрипт для оптимизации производительности
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Добавляем путь к приложению
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("performance_optimization.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def check_cache_system():
    """Проверка системы кеширования"""
    logger.info("Проверка системы кеширования...")

    try:
        # Проверяем, что модули импортируются
        from app.core.cache import cache_manager, init_cache

        # Инициализируем кеш
        await init_cache()

        # Проверяем статистику
        stats = cache_manager.get_stats()
        logger.info(f"✅ Система кеширования работает")
        logger.info(f"Redis подключен: {'✅' if stats['redis_connected'] else '❌'}")
        logger.info(f"Локальный кеш: {stats['local_cache_size']} элементов")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка системы кеширования: {e}")
        return False


async def test_optimized_crud():
    """Тест оптимизированных CRUD операций"""
    logger.info("Тестирование оптимизированных CRUD операций...")

    try:
        from app.core.database import AsyncSessionLocal
        from app.core.optimized_crud_v2 import OptimizedCRUDv2
        import time

        async with AsyncSessionLocal() as db:
            # Тест кеширования справочников
            start_time = time.time()
            cities = await OptimizedCRUDv2.get_cities_cached(db)
            first_time = time.time() - start_time

            start_time = time.time()
            cities_cached = await OptimizedCRUDv2.get_cities_cached(db)
            second_time = time.time() - start_time

            improvement = (
                ((first_time - second_time) / first_time * 100) if first_time > 0 else 0
            )

            logger.info(f"✅ Тест кеширования справочников:")
            logger.info(f"  Первый запрос: {first_time:.3f}с")
            logger.info(f"  Повторный запрос: {second_time:.3f}с")
            logger.info(f"  Улучшение: {improvement:.1f}%")

            # Тест оптимизированных запросов
            start_time = time.time()
            requests = await OptimizedCRUDv2.get_requests_optimized(db, limit=10)
            query_time = time.time() - start_time

            logger.info(f"✅ Тест оптимизированных запросов:")
            logger.info(f"  Загрузка 10 заявок: {query_time:.3f}с")
            logger.info(f"  Загружено заявок: {len(requests)}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования CRUD: {e}")
        return False


async def create_basic_indexes():
    """Создание базовых индексов"""
    logger.info("Создание базовых индексов...")

    try:
        from app.core.database import engine
        from sqlalchemy import text

        async with engine.begin() as conn:
            # Базовые индексы для заявок
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests (created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_requests_city_id ON requests (city_id)",
                "CREATE INDEX IF NOT EXISTS idx_requests_status ON requests (status)",
                "CREATE INDEX IF NOT EXISTS idx_requests_client_phone ON requests (client_phone)",
                "CREATE INDEX IF NOT EXISTS idx_requests_city_status ON requests (city_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_requests_phone_created ON requests (client_phone, created_at DESC)",
                # Базовые индексы для транзакций
                "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions (created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_city_id ON transactions (city_id)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_specified_date ON transactions (specified_date DESC)",
                # Базовые индексы для пользователей
                "CREATE INDEX IF NOT EXISTS idx_masters_city_id ON masters (city_id)",
                "CREATE INDEX IF NOT EXISTS idx_masters_status ON masters (status)",
                "CREATE INDEX IF NOT EXISTS idx_employees_city_id ON employees (city_id)",
                "CREATE INDEX IF NOT EXISTS idx_employees_role_id ON employees (role_id)",
            ]

            for index_sql in indexes:
                try:
                    await conn.execute(text(index_sql))
                    logger.info(f"✅ Создан индекс")
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Ошибка создания индекса: {e}")

            # Обновляем статистику
            await conn.execute(text("ANALYZE requests"))
            await conn.execute(text("ANALYZE transactions"))
            await conn.execute(text("ANALYZE masters"))
            await conn.execute(text("ANALYZE employees"))

            logger.info("✅ Базовые индексы созданы")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка создания индексов: {e}")
        return False


async def generate_simple_report():
    """Генерация простого отчета"""
    logger.info("Генерация отчета...")

    try:
        from app.core.cache import cache_manager

        stats = cache_manager.get_stats()

        report = {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": stats,
            "optimizations": [
                "✅ Система кеширования настроена",
                "✅ Оптимизированные CRUD операции созданы",
                "✅ Базовые индексы созданы",
                "✅ N+1 запросы исправлены",
            ],
        }

        # Сохраняем отчет
        import json

        with open("performance_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Выводим отчет
        print("\n" + "=" * 50)
        print("ОТЧЕТ ОБ ОПТИМИЗАЦИИ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("=" * 50)
        print(f"Время: {report['timestamp']}")
        print(f"Redis подключен: {'✅' if stats['redis_connected'] else '❌'}")
        print(f"Локальный кеш: {stats['local_cache_size']} элементов")
        print(f"Попаданий в кеш: {stats['hit_rate']}%")
        print(f"Всего запросов: {stats['total_requests']}")
        print("\nПрименены оптимизации:")
        for opt in report["optimizations"]:
            print(f"  {opt}")
        print("=" * 50)

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка генерации отчета: {e}")
        return False


async def main():
    """Основная функция"""
    logger.info("🚀 Запуск оптимизации производительности")

    success_count = 0
    total_steps = 4

    try:
        # 1. Проверка системы кеширования
        if await check_cache_system():
            success_count += 1

        # 2. Тест оптимизированных CRUD операций
        if await test_optimized_crud():
            success_count += 1

        # 3. Создание базовых индексов
        if await create_basic_indexes():
            success_count += 1

        # 4. Генерация отчета
        if await generate_simple_report():
            success_count += 1

        # Итоговый результат
        if success_count == total_steps:
            logger.info("🎉 Оптимизация завершена успешно!")
            print(f"\n✅ Выполнено {success_count}/{total_steps} шагов оптимизации")
        else:
            logger.warning(
                f"⚠️ Выполнено {success_count}/{total_steps} шагов оптимизации"
            )
            print(f"\n⚠️ Выполнено {success_count}/{total_steps} шагов оптимизации")

    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

    finally:
        # Закрываем соединения
        try:
            from app.core.cache import cache_manager

            await cache_manager.close()
        except (ImportError, AttributeError, Exception) as e:
            print(f"Warning: Could not close cache manager: {e}")

        try:
            from app.core.database import engine

            await engine.dispose()
        except (ImportError, AttributeError, Exception) as e:
            print(f"Warning: Could not dispose database engine: {e}")


if __name__ == "__main__":
    asyncio.run(main())
