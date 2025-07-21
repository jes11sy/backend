# 🚀 Backend CI/CD Setup

## 🎯 Что настроено

- ✅ **Quality Checks**: flake8, black, mypy, bandit, safety
- ✅ **Tests**: pytest с coverage, PostgreSQL, Redis
- ✅ **Docker Build**: production-ready образ
- ✅ **Database Migrations**: автоматические Alembic миграции  
- ✅ **SSH Deploy**: docker-compose на продакшн сервере
- ✅ **Health Checks**: проверка API после деплоя
- ✅ **Performance Tests**: базовые нагрузочные тесты

## 🔧 Настройка GitHub Secrets

Добавь эти секреты в GitHub репозиторий:

### 🔐 SSH Деплой
```
DEPLOY_SSH_KEY      # Приватный SSH ключ для деплоя
DEPLOY_HOST         # lead-schem.ru
DEPLOY_USER         # username на сервере
DEPLOY_PATH         # /var/www/backend или /home/user/backend
```

### 🗄️ База данных
```
DATABASE_URL        # postgresql+asyncpg://user:pass@host:5432/db
```

### ⚙️ Environment Variables
```
SECRET_KEY          # 64+ char secret for FastAPI
JWT_SECRET_KEY      # 64+ char secret for JWT
REDIS_PASSWORD      # Redis password
POSTGRESQL_PASSWORD # PostgreSQL password
```

## 📋 GitHub Secrets Setup

1. **Зайди в GitHub репозиторий**
2. **Settings → Secrets and variables → Actions**
3. **New repository secret**

### SSH Key Setup:
```bash
# На сервере сгенерируй SSH ключ
ssh-keygen -t rsa -b 4096 -C "github-actions@lead-schem.ru"

# Добавь публичный ключ в authorized_keys
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

# Скопируй приватный ключ в GitHub Secrets
cat ~/.ssh/id_rsa
```

## 🐳 Production Server Setup

### 1. Docker & Docker Compose
```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Directory Structure
```bash
# Создай структуру директорий
sudo mkdir -p /var/www/backend
sudo chown -R $USER:$USER /var/www/backend
cd /var/www/backend

# Папки для данных
mkdir -p {media,data,logs}
mkdir -p media/{zayvka/{bso,rashod,zapis},gorod/rashod}
```

### 3. Environment File
```bash
# Скопируй и заполни .env файл
cp deployment/.env.production.example .env.production
nano .env.production
```

### 4. Database Setup
```bash
# PostgreSQL (если не через Docker)
sudo apt install postgresql postgresql-contrib
sudo -u postgres createdb backend_production
sudo -u postgres createuser backend_user

# Redis (если не через Docker)  
sudo apt install redis-server
sudo systemctl enable redis-server
```

## 🚀 Manual Deploy Test

Проверь деплой вручную:

```bash
# На сервере
cd /var/www/backend

# Загрузи Docker образ (будет автоматически через CI/CD)
# docker load < backend-image.tar.gz

# Запуск через docker-compose
docker-compose -f docker-compose.production.yml up -d

# Проверка статуса
docker-compose -f docker-compose.production.yml ps

# Логи
docker-compose -f docker-compose.production.yml logs -f backend

# Проверка API
curl https://api.lead-schem.ru/api/health
curl https://api.lead-schem.ru/docs
```

## 🔍 Workflow Overview

### 1. **Quality Checks** (на каждый push/PR)
- Python linting (flake8)
- Code formatting (black) 
- Type checking (mypy)
- Security scan (bandit)
- Dependency safety (safety)
- Unit/integration tests (pytest)
- Coverage reports

### 2. **Build** (на каждый push)
- Docker образ сборка
- Тестирование образа
- Сохранение артефакта

### 3. **Deploy** (только main branch)
- SSH подключение к серверу
- Загрузка Docker образа
- Database migrations
- Graceful restart сервисов
- Health check verification

### 4. **Performance Tests** (после деплоя)
- API response time
- Basic load testing
- Documentation accessibility

## 📊 Monitoring После Деплоя

### Health Checks:
```bash
# API Health
curl https://api.lead-schem.ru/api/health

# Database Health  
curl https://api.lead-schem.ru/api/health/database

# Services Status
curl https://api.lead-schem.ru/api/health/services
```

### Docker Status:
```bash
# Контейнеры
docker-compose -f docker-compose.production.yml ps

# Ресурсы
docker stats

# Логи
docker-compose -f docker-compose.production.yml logs -f
```

### Database:
```bash
# Подключение к БД
docker-compose -f docker-compose.production.yml exec backend python -c "
from app.core.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT version()')
        print(result.scalar())
asyncio.run(test())
"
```

## 🚨 Troubleshooting

### CI/CD Fails:

**Tests fail:**
```bash
# Локально запусти тесты
cd backend
python -m pytest tests/ -v
```

**Docker build fails:**
```bash
# Проверь Dockerfile локально
cd backend
docker build -f deployment/Dockerfile.production -t test .
```

**SSH deploy fails:**
```bash
# Проверь SSH доступ
ssh -i ~/.ssh/id_rsa user@lead-schem.ru

# Проверь права
ls -la /var/www/backend
```

### Production Issues:

**API недоступен:**
```bash
# Проверь контейнеры
docker ps
docker-compose logs backend

# Проверь порты
sudo netstat -tlnp | grep :8000
```

**Database errors:**
```bash
# Проверь подключение к БД
docker-compose exec postgres psql -U backend_user -d backend_production

# Проверь миграции
docker-compose exec backend alembic current
docker-compose exec backend alembic upgrade head
```

**SSL/HTTPS errors:**
```bash
# Проверь сертификаты
sudo nginx -t
sudo systemctl status nginx

# Проверь домен
dig api.lead-schem.ru
curl -I https://api.lead-schem.ru
```

## 🔄 Updates & Rollback

### Автоматический деплой:
- Push в `main` → автоматический CI/CD
- Pull Request → только тесты

### Ручной rollback:
```bash
# Список образов
docker images | grep backend-api

# Откат к предыдущему образу
docker tag backend-api:previous backend-api:latest
docker-compose -f docker-compose.production.yml up -d
```

### Database rollback:
```bash
# Откат миграций
docker-compose exec backend alembic downgrade -1
```

## 📈 Оптимизация

### Performance:
- Увеличь `WORKERS` в .env.production
- Настрой `POOL_SIZE` для БД
- Оптимизируй `CACHE_TTL`

### Security:
- Ротация секретов каждые 90 дней
- Мониторинг банов (bandit) в CI
- Обновление зависимостей (safety)

### Monitoring:
- Подключи Grafana/Prometheus
- Настрой алерты в Telegram
- Логи в ELK stack 