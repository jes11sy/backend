# 🗄️ Подключение к внешней базе данных

## Обзор

Система настроена для работы с **внешней PostgreSQL базой данных** вместо создания собственного контейнера. Это позволяет использовать существующую инфраструктуру БД.

---

## 🔧 Настройка подключения

### 1. Переменные окружения

Скопируйте и настройте файл конфигурации:

```bash
cp deployment/env.production.example deployment/.env.production
```

Заполните параметры вашей БД:

```env
# Обязательные параметры
POSTGRESQL_HOST=your-db-server.com
POSTGRESQL_PORT=5432
POSTGRESQL_USER=your_db_user
POSTGRESQL_PASSWORD=your_secure_password
POSTGRESQL_DBNAME=your_database_name

# Настройки пула подключений
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# SSL настройки (опционально)
DB_SSL_MODE=require
DB_SSL_CERT_PATH=/path/to/client-cert.pem
DB_SSL_KEY_PATH=/path/to/client-key.pem
DB_SSL_CA_PATH=/path/to/ca-cert.pem
```

### 2. SSL конфигурация

Для безопасного подключения рекомендуется использовать SSL:

#### Режимы SSL:
- `disable` - без SSL (не рекомендуется)
- `prefer` - SSL если доступен
- `require` - обязательный SSL
- `verify-ca` - проверка сертификата CA
- `verify-full` - полная проверка сертификата и хоста

#### Настройка сертификатов:
```bash
# Создайте директорию для сертификатов
mkdir -p /opt/backend/ssl

# Скопируйте сертификаты
cp client-cert.pem /opt/backend/ssl/
cp client-key.pem /opt/backend/ssl/
cp ca-cert.pem /opt/backend/ssl/

# Установите права
chmod 600 /opt/backend/ssl/client-key.pem
chmod 644 /opt/backend/ssl/client-cert.pem
chmod 644 /opt/backend/ssl/ca-cert.pem
```

---

## 🧪 Тестирование подключения

### Локальное тестирование

```bash
# Установите переменные окружения
export POSTGRESQL_HOST=your-db-host
export POSTGRESQL_USER=your-user
export POSTGRESQL_PASSWORD=your-password
export POSTGRESQL_DBNAME=your-db

# Запустите тест подключения
python scripts/test_external_db.py
```

### Через Docker

```bash
# Создайте .env файл с параметрами БД
echo "POSTGRESQL_HOST=your-db-host" > .env
echo "POSTGRESQL_USER=your-user" >> .env
echo "POSTGRESQL_PASSWORD=your-password" >> .env
echo "POSTGRESQL_DBNAME=your-db" >> .env

# Запустите тестовый контейнер
docker run --rm -it \
  --env-file .env \
  python:3.11-slim \
  bash -c "pip install asyncpg sqlalchemy && python test_external_db.py"
```

---

## 🔄 Миграции базы данных

### Применение миграций

```bash
# Локально (если есть доступ к БД)
alembic upgrade head

# Через backend контейнер
docker-compose -f deployment/docker-compose.production.yml exec backend \
  alembic upgrade head
```

### Проверка статуса миграций

```bash
# Текущая версия
alembic current

# История миграций  
alembic history

# Показать SQL для миграции
alembic upgrade head --sql
```

---

## 🔐 Настройки безопасности

### 1. Создание пользователя БД

```sql
-- Создание пользователя для приложения
CREATE USER backend_app WITH PASSWORD 'secure_password';

-- Предоставление минимальных прав
GRANT CONNECT ON DATABASE your_database TO backend_app;
GRANT USAGE ON SCHEMA public TO backend_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO backend_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO backend_app;

-- Права на будущие таблицы
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO backend_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
  GRANT USAGE, SELECT ON SEQUENCES TO backend_app;
```

### 2. Настройка файрвола

Разрешите подключения только с серверов приложения:

```bash
# Пример для UFW
sudo ufw allow from YOUR_APP_SERVER_IP to any port 5432

# Пример для iptables  
iptables -A INPUT -p tcp --dport 5432 -s YOUR_APP_SERVER_IP -j ACCEPT
```

### 3. Конфигурация PostgreSQL

В `postgresql.conf`:
```conf
# Подключения
listen_addresses = 'localhost,YOUR_DB_SERVER_IP'
max_connections = 200

# SSL
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_ca_file = 'ca.crt'

# Логирование
log_connections = on
log_disconnections = on
log_statement = 'mod'
```

В `pg_hba.conf`:
```conf
# Подключения для приложения
hostssl your_database backend_app YOUR_APP_SERVER_IP/32 md5
```

---

## 📊 Мониторинг подключений

### Проверка активных подключений

```sql
-- Активные подключения
SELECT pid, usename, application_name, client_addr, state
FROM pg_stat_activity 
WHERE state = 'active';

-- Подключения от приложения
SELECT count(*) as connections
FROM pg_stat_activity 
WHERE application_name = 'lead_schem_backend';
```

### Мониторинг производительности

```sql
-- Размер БД
SELECT pg_size_pretty(pg_database_size('your_database'));

-- Топ медленных запросов
SELECT query, mean_time, calls
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

---

## 🚨 Troubleshooting

### Частые ошибки

#### 1. Connection refused
```
❌ could not connect to server: Connection refused
```
**Решение:**
- Проверьте доступность сервера БД
- Убедитесь что PostgreSQL запущен
- Проверьте настройки файрвола

#### 2. SSL required
```
❌ SSL connection is required
```
**Решение:**
```env
DB_SSL_MODE=require
```

#### 3. Authentication failed
```
❌ FATAL: password authentication failed
```
**Решение:**
- Проверьте логин и пароль
- Убедитесь что пользователь существует
- Проверьте настройки pg_hba.conf

#### 4. Database does not exist
```
❌ FATAL: database "your_db" does not exist
```
**Решение:**
```sql
CREATE DATABASE your_database_name;
```

### Логи диагностики

```bash
# Логи PostgreSQL
tail -f /var/log/postgresql/postgresql-13-main.log

# Логи приложения
docker-compose logs -f backend

# Подробные логи подключений
export PYTHONPATH=/app
export SQLALCHEMY_ECHO=True
python scripts/test_external_db.py
```

---

## ✅ Чек-лист готовности

Перед деплоем убедитесь:

- [ ] БД доступна по сети
- [ ] Пользователь создан с правильными правами
- [ ] SSL настроен (если требуется)
- [ ] Файрвол настроен
- [ ] Тестирование подключения успешно
- [ ] Миграции применены
- [ ] Переменные окружения настроены
- [ ] Backup/restore процедуры готовы

После этого можно запускать продакшен деплой! 🚀 