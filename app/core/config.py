try:
    from pydantic_settings import BaseSettings  # type: ignore[import]
except ImportError:
    from pydantic import BaseSettings  # type: ignore[import,no-redef]
from typing import Optional, List
import secrets
import os


class Settings(BaseSettings):
    # Database settings
    POSTGRESQL_HOST: str
    POSTGRESQL_PORT: int = 5432
    POSTGRESQL_USER: str
    POSTGRESQL_PASSWORD: str
    POSTGRESQL_DBNAME: str

    # Database pool settings
    DB_POOL_SIZE: int = 10  # Базовое количество соединений в пуле
    DB_MAX_OVERFLOW: int = 20  # Дополнительные соединения при пиковой нагрузке
    DB_POOL_TIMEOUT: int = 30  # Таймаут ожидания соединения (секунды)
    DB_POOL_RECYCLE: int = 3600  # Время жизни соединения (секунды) - 1 час

    # Redis settings for caching
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    # Cache settings
    CACHE_TTL: int = 3600  # 1 час
    CACHE_ENABLED: bool = True
    CACHE_KEY_PREFIX: str = "request_system"

    @property
    def get_redis_url(self) -> str:
        """Получить URL подключения к Redis"""
        if self.REDIS_URL:
            return self.REDIS_URL

        auth = ""
        if self.REDIS_PASSWORD:
            auth = f":{self.REDIS_PASSWORD}@"

        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRESQL_USER}:{self.POSTGRESQL_PASSWORD}@{self.POSTGRESQL_HOST}:{self.POSTGRESQL_PORT}/{self.POSTGRESQL_DBNAME}"

    # Security settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Environment setting
    ENVIRONMENT: str = "development"

    # File upload settings
    UPLOAD_DIR: str = "media"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: str = "jpg,jpeg,png,gif,pdf,doc,docx,mp3,wav"
    MAX_FILES_PER_USER: int = 100

    @property
    def get_allowed_file_types(self) -> List[str]:
        """Получить список разрешенных типов файлов"""
        return [ext.strip().lower() for ext in self.ALLOWED_FILE_TYPES.split(",")]

    # Security settings
    DEBUG: bool = False
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    RATE_LIMIT_PER_MINUTE: int = 100
    LOGIN_ATTEMPTS_PER_HOUR: int = 5

    @property
    def get_allowed_hosts(self) -> List[str]:
        """Получить список разрешенных хостов"""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"

    # Rambler IMAP settings for call recordings
    RAMBLER_IMAP_HOST: str = "imap.rambler.ru"
    RAMBLER_IMAP_PORT: int = 993
    RAMBLER_IMAP_USERNAME: Optional[str] = None
    RAMBLER_IMAP_PASSWORD: Optional[str] = None
    RAMBLER_IMAP_USE_SSL: bool = True

    # Call recordings settings
    RECORDINGS_CHECK_INTERVAL: int = 300  # 5 minutes

    # Telegram alerts settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[int] = None
    TELEGRAM_ALERTS_ENABLED: bool = False

    # Mango webhook security settings
    MANGO_WEBHOOK_SECRET: Optional[str] = None
    MANGO_ALLOWED_IPS: str = ""  # Comma-separated list of allowed IPs

    @property
    def get_mango_allowed_ips(self) -> List[str]:
        """Получить список разрешенных IP адресов для Mango webhook"""
        if self.MANGO_ALLOWED_IPS:
            return [ip.strip() for ip in self.MANGO_ALLOWED_IPS.split(",")]
        return []

    @property
    def RECORDINGS_DOWNLOAD_PATH(self) -> str:
        """Получение пути для сохранения записей"""
        # Используем относительный путь от корня приложения
        return os.path.join("media", "zayvka", "zapis")

    # CORS settings
    ALLOWED_ORIGINS: str = ""
    CORS_ORIGINS: str = ""

    def get_allowed_origins(self) -> List[str]:
        """Получить разрешенные origins для CORS"""
        # Приоритет: CORS_ORIGINS -> ALLOWED_ORIGINS -> defaults
        origins_str = self.CORS_ORIGINS or self.ALLOWED_ORIGINS

        if origins_str:
            return [origin.strip() for origin in origins_str.split(",")]

        # Для разработки разрешаем все localhost origins
        if self.ENVIRONMENT == "development":
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://master.lead-schem.ru/",
            ]

        # Для продакшена должны быть указаны конкретные origins
        return []

    def get_cors_origin_header(self) -> str:
        """Получить origin для CORS заголовков в ответах API"""
        allowed_origins = self.get_allowed_origins()

        # Для разработки возвращаем localhost
        if self.ENVIRONMENT == "development":
            return "http://localhost:3000"

        # Для продакшена возвращаем первый разрешенный origin или fallback
        if allowed_origins:
            # Предпочитаем HTTPS origins
            https_origins = [
                origin for origin in allowed_origins if origin.startswith("https://")
            ]
            if https_origins:
                return https_origins[0]
            return allowed_origins[0]

        # Fallback для продакшена
        return "https://lead-schem.ru"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Проверяем обязательность SECRET_KEY
        if not self.SECRET_KEY:
            raise ValueError(
                "🚨 SECRET_KEY is required! Please set it in .env file.\n"
                'Generate one using: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

        # Проверяем, что SECRET_KEY не является примером
        if self.SECRET_KEY in [
            "your-secret-key-here",
            "your-very-secure-secret-key-here-min-32-chars",
        ]:
            raise ValueError(
                "🚨 Please set a real SECRET_KEY in .env file, not the example value!\n"
                'Generate one using: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

        # Проверяем минимальную длину SECRET_KEY
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                f"🚨 SECRET_KEY is too short ({len(self.SECRET_KEY)} chars). Minimum: 32 characters.\n"
                'Generate a secure one using: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

        # Дополнительная проверка для продакшена
        if self.ENVIRONMENT == "production":
            if len(self.SECRET_KEY) < 64:
                print(
                    "⚠️  WARNING: For production, SECRET_KEY should be at least 64 characters long!"
                )

            # Проверяем энтропию ключа
            if self.SECRET_KEY.isalnum() or len(set(self.SECRET_KEY)) < 16:
                print(
                    "⚠️  WARNING: SECRET_KEY appears to have low entropy. Use a cryptographically secure random key!"
                )


settings = Settings()
