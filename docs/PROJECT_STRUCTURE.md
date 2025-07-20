# Структура проекта Backend

## Содержание
1. [Общая структура](#общая-структура)
2. [Директория app/](#директория-app)
3. [Конфигурация](#конфигурация)
4. [Деплой](#деплой)
5. [Тесты](#тесты)
6. [Скрипты](#скрипты)
7. [Документация](#документация)

## Общая структура

```
backend/
├── app/                          # Основное приложение
│   ├── __init__.py
│   ├── main.py                   # Точка входа FastAPI
│   ├── api/                      # API эндпоинты
│   ├── core/                     # Основная логика
│   ├── middleware/               # Промежуточное ПО
│   ├── monitoring/               # Мониторинг и метрики
│   ├── services/                 # Внешние сервисы
│   └── utils/                    # Утилиты
├── alembic/                      # Миграции базы данных
├── config/                       # Конфигурационные файлы
├── deployment/                   # Docker и деплой
├── docs/                         # Документация
├── logs/                         # Логи приложения
├── media/                        # Загруженные файлы
├── monitoring/                   # Конфигурация мониторинга
├── scripts/                      # Скрипты управления
├── tests/                        # Тесты
└── requirements.txt              # Зависимости Python
```

## Директория app/

### main.py
Главный файл приложения FastAPI:
- Настройка CORS
- Подключение middleware
- Регистрация роутеров
- Статические файлы
- Lifespan events

### api/
Все API эндпоинты разделены по модулям:

```
api/
├── __init__.py
├── auth.py                       # Аутентификация
├── requests.py                   # Заявки
├── transactions.py               # Транзакции
├── users.py                      # Пользователи
├── files.py                      # Загрузка файлов
├── file_access.py               # Доступ к файлам
├── mango.py                     # Webhook Mango
├── recordings.py                # Записи звонков
├── health.py                    # Здоровье системы
├── metrics.py                   # Метрики
├── monitoring.py                # Мониторинг
├── v1/                          # API версии 1
│   └── router.py
└── v2/                          # API версии 2
    └── router.py
```

### core/
Основная бизнес-логика:

```
core/
├── __init__.py
├── config.py                    # Настройки приложения
├── database.py                  # Подключение к БД
├── models.py                    # SQLAlchemy модели
├── schemas.py                   # Pydantic схемы
├── crud.py                      # CRUD операции
├── auth.py                      # Логика аутентификации
├── security.py                 # Безопасность
├── cache.py                     # Кеширование Redis
├── exceptions.py                # Исключения
└── versioning.py                # Версионирование API
```

### middleware/
Промежуточное ПО:

```
middleware/
├── __init__.py
└── error_handler.py             # Обработка ошибок
```

### monitoring/
Система мониторинга:

```
monitoring/
├── __init__.py
├── alerts.py                    # Система алертов
├── metrics.py                   # Сбор метрик
├── prometheus_metrics.py        # Метрики Prometheus
├── connection_pool_monitor.py   # Мониторинг пула соединений
├── redis_monitor.py            # Мониторинг Redis
├── external_services.py        # Мониторинг внешних сервисов
└── telegram_alerts.py          # Telegram уведомления
```

### services/
Внешние сервисы:

```
services/
├── __init__.py
├── email_client.py              # IMAP клиент Rambler
└── recording_service.py         # Сервис записей звонков
```

### utils/
Утилиты:

```
utils/
├── file_security.py             # Безопасность файлов
└── subprocess_security.py       # Безопасность подпроцессов
```

## Конфигурация

### config/
```
config/
├── alembic.ini                  # Настройки Alembic
├── env.example                  # Пример переменных окружения
└── pytest.ini                  # Настройки pytest
```

### Переменные окружения (.env)
```bash
# База данных
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=password
POSTGRESQL_DBNAME=requests_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Безопасность
SECRET_KEY=your-secret-key
ALGORITHM=HS256

# Rambler для записей звонков
RAMBLER_IMAP_USERNAME=email@rambler.ru
RAMBLER_IMAP_PASSWORD=password

# Mango webhook
MANGO_WEBHOOK_SECRET=secret
MANGO_ALLOWED_IPS=ip1,ip2

# CORS
CORS_ORIGINS=https://lead-schem.ru,https://www.lead-schem.ru
```

## Деплой

### deployment/
```
deployment/
├── Dockerfile                   # Dockerfile для разработки
├── Dockerfile.production        # Dockerfile для продакшена
├── docker-compose.yml          # Композиция для разработки
├── docker-compose.production.yml # Композиция для продакшена
├── env.production.example       # Пример продакшн переменных
├── kong/                        # API Gateway Kong
├── nginx/                       # Nginx конфигурация
├── traefik/                     # Traefik конфигурация
└── monitoring/                  # Мониторинг инфраструктуры
    ├── prometheus_config/
    ├── grafana_dashboards/
    └── grafana_provisioning/
```

### Dockerfile.production
```dockerfile
FROM python:3.11-slim

# Создаем пользователя
RUN useradd --create-home --shell /bin/bash appuser

# Рабочая директория
WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Создаем необходимые директории
RUN mkdir -p media/zayvka/bso media/zayvka/rashod media/zayvka/zapis media/gorod/rashod
RUN chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Тесты

### tests/
```
tests/
├── __init__.py
├── conftest.py                  # Фикстуры pytest
├── test_api.py                  # Тесты API
├── test_auth.py                 # Тесты аутентификации
├── test_models.py               # Тесты моделей
├── test_security.py             # Тесты безопасности
├── test_performance.py          # Тесты производительности
├── test_integration.py          # Интеграционные тесты
└── test_e2e.py                  # End-to-end тесты
```

### Запуск тестов
```bash
# Все тесты
pytest

# Только быстрые тесты
pytest -m "not slow"

# С покрытием
pytest --cov=app --cov-report=html

# Определенный модуль
pytest tests/test_api.py
```

## Скрипты

### scripts/
```
scripts/
├── run_dev.py                   # Запуск в режиме разработки
├── run_tests.py                 # Запуск тестов
├── create_admin.py              # Создание администратора
├── check_db.py                  # Проверка базы данных
├── optimize_database.py         # Оптимизация БД
├── manage_migrations.py         # Управление миграциями
├── deploy_production.sh         # Деплой в продакшн
└── test_cors.py                 # Тестирование CORS
```

### Примеры использования
```bash
# Запуск разработки
python scripts/run_dev.py

# Создание администратора
python scripts/create_admin.py

# Проверка БД
python scripts/check_db.py

# Деплой
./scripts/deploy_production.sh
```

## Документация

### docs/
```
docs/
├── README.md                    # Основная документация
├── API_COMPLETE_GUIDE.md        # Полное руководство по API
├── PROJECT_STRUCTURE.md         # Структура проекта
├── FRONTEND_FILE_URLS.md        # Правильные URL для файлов
├── SECURITY_GUIDE.md            # Руководство по безопасности
├── MONITORING.md                # Мониторинг и метрики
├── DEPLOYMENT_STATUS.md         # Статус деплоя
└── CHANGELOG_SECURITY.md        # Изменения безопасности
```

## Файловая система

### media/
Структура для загруженных файлов:
```
media/
├── zayvka/                      # Файлы заявок
│   ├── bso/                     # БСО документы
│   ├── rashod/                  # Расходные документы
│   └── zapis/                   # Аудиозаписи
└── gorod/                       # Файлы транзакций
    └── rashod/                  # Расходные документы
```

### logs/
Логи приложения:
```
logs/
├── app.log                      # Основные логи
├── error.log                    # Логи ошибок
├── access.log                   # Логи доступа
└── security.log                 # Логи безопасности
```

## Алгоритм разработки

### 1. Новая функция
1. Создать ветку: `git checkout -b feature/new-feature`
2. Добавить модель в `core/models.py`
3. Создать схемы в `core/schemas.py`
4. Добавить CRUD в `core/crud.py`
5. Создать API в `api/`
6. Написать тесты в `tests/`
7. Обновить документацию
8. Создать PR

### 2. Миграция БД
```bash
# Создать миграцию
alembic revision --autogenerate -m "Description"

# Применить миграцию
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

### 3. Деплой
```bash
# Локальное тестирование
docker-compose up --build

# Продакшн деплой
git push origin main  # Автоматический деплой через GitLab CI
```

## Мониторинг

### Prometheus метрики
- HTTP запросы: счетчики, гистограммы
- Подключения к БД: активные, использование пула
- Redis: hit rate, память
- Файловая система: место на диске

### Grafana дашборды
- Системные метрики
- Производительность API
- Ошибки и алерты
- Пользовательская активность

### Алерты
- Высокая нагрузка CPU/память
- Ошибки 5XX превышают порог
- Недоступность внешних сервисов
- Проблемы с базой данных

## Безопасность

### Принципы
- Валидация всех входных данных
- Проверка файлов на безопасность
- Rate limiting
- CORS политики
- JWT токены с истечением
- Логирование всех операций

### Проверки
- Сканирование зависимостей: `safety check`
- Линтинг безопасности: `bandit`
- Проверка секретов: `detect-secrets`
- Аудит Docker образов 