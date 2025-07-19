"""
Конфигурация подключения к внешней базе данных
"""

import os
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from .config import settings


def create_external_db_engine():
    """
    Создание движка для подключения к внешней базе данных
    с поддержкой SSL и оптимизированными настройками
    """
    
    # Базовый URL подключения
    database_url = (
        f"postgresql+asyncpg://{settings.POSTGRESQL_USER}:"
        f"{settings.POSTGRESQL_PASSWORD}@{settings.POSTGRESQL_HOST}:"
        f"{settings.POSTGRESQL_PORT}/{settings.POSTGRESQL_DBNAME}"
    )
    
    # SSL параметры
    ssl_context = None
    connect_args = {}
    
    # Настройка SSL если указан режим
    ssl_mode = os.getenv('DB_SSL_MODE', 'prefer')
    if ssl_mode in ['require', 'verify-ca', 'verify-full']:
        ssl_context = ssl.create_default_context()
        
        # Пути к SSL сертификатам
        ssl_cert_path = os.getenv('DB_SSL_CERT_PATH')
        ssl_key_path = os.getenv('DB_SSL_KEY_PATH') 
        ssl_ca_path = os.getenv('DB_SSL_CA_PATH')
        
        if ssl_cert_path and ssl_key_path:
            ssl_context.load_cert_chain(ssl_cert_path, ssl_key_path)
        
        if ssl_ca_path:
            ssl_context.load_verify_locations(ssl_ca_path)
        
        if ssl_mode == 'verify-full':
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
        elif ssl_mode == 'verify-ca':
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:  # require
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        connect_args['ssl'] = ssl_context
    
    # Дополнительные параметры подключения
    connect_args.update({
        'command_timeout': 60,
        'server_settings': {
            'application_name': 'lead_schem_backend',
            'search_path': 'public',
        }
    })
    
    # Создание движка с оптимизированными настройками
    engine = create_async_engine(
        database_url,
        # Connection Pool настройки
        poolclass=QueuePool,
        pool_size=int(os.getenv('DB_POOL_SIZE', settings.DB_POOL_SIZE)),
        max_overflow=int(os.getenv('DB_MAX_OVERFLOW', settings.DB_MAX_OVERFLOW)),
        pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', settings.DB_POOL_TIMEOUT)),
        pool_recycle=int(os.getenv('DB_POOL_RECYCLE', settings.DB_POOL_RECYCLE)),
        pool_pre_ping=True,  # Проверка соединений перед использованием
        
        # Дополнительные настройки
        connect_args=connect_args,
        echo=False,  # В продакшене отключаем SQL логи
        echo_pool=False,
        future=True,
        
        # Retry настройки
        pool_reset_on_return='commit',
    )
    
    return engine


def create_external_db_session():
    """
    Создание фабрики сессий для внешней БД
    """
    engine = create_external_db_engine()
    
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False
    )
    
    return async_session


# Проверка подключения к внешней БД
async def check_external_db_connection():
    """
    Проверка подключения к внешней базе данных
    """
    try:
        engine = create_external_db_engine()
        
        async with engine.begin() as conn:
            # Проверочный запрос
            result = await conn.execute("SELECT 1 as test")
            row = result.fetchone()
            
            if row and row[0] == 1:
                print("✅ Подключение к внешней БД успешно")
                return True
            else:
                print("❌ Ошибка проверочного запроса к внешней БД")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка подключения к внешней БД: {e}")
        return False
    finally:
        await engine.dispose()


# Получение информации о БД
async def get_external_db_info():
    """
    Получение информации о внешней базе данных
    """
    try:
        engine = create_external_db_engine()
        
        async with engine.begin() as conn:
            # Версия PostgreSQL
            version_result = await conn.execute("SELECT version()")
            version = version_result.fetchone()[0]
            
            # Размер БД
            size_result = await conn.execute(
                f"SELECT pg_size_pretty(pg_database_size('{settings.POSTGRESQL_DBNAME}'))"
            )
            db_size = size_result.fetchone()[0]
            
            # Количество подключений
            connections_result = await conn.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            active_connections = connections_result.fetchone()[0]
            
            return {
                'version': version,
                'database_size': db_size,
                'active_connections': active_connections,
                'host': settings.POSTGRESQL_HOST,
                'port': settings.POSTGRESQL_PORT,
                'database': settings.POSTGRESQL_DBNAME,
                'user': settings.POSTGRESQL_USER
            }
            
    except Exception as e:
        print(f"❌ Ошибка получения информации о БД: {e}")
        return None
    finally:
        await engine.dispose()


# Миграции для внешней БД
async def run_migrations_external_db():
    """
    Запуск миграций для внешней базы данных
    """
    import subprocess
    import sys
    
    try:
        # Устанавливаем переменные окружения для Alembic
        env = os.environ.copy()
        env['DATABASE_URL'] = (
            f"postgresql://{settings.POSTGRESQL_USER}:"
            f"{settings.POSTGRESQL_PASSWORD}@{settings.POSTGRESQL_HOST}:"
            f"{settings.POSTGRESQL_PORT}/{settings.POSTGRESQL_DBNAME}"
        )
        
        # Запуск миграций
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Миграции применены успешно")
            return True
        else:
            print(f"❌ Ошибка применения миграций: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запуска миграций: {e}")
        return False 