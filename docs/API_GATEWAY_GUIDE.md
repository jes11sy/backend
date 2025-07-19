# 🌐 API Gateway - Руководство по централизованному управлению

## 🎯 Что такое API Gateway

**API Gateway** — это единая точка входа для всех API запросов в вашей системе. Он выступает как "умный прокси" между клиентами и backend сервисами.

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│   Клиенты   │───▶│   API Gateway   │───▶│  Backend    │
│ Web/Mobile  │    │     (Kong)      │    │  Services   │
└─────────────┘    └─────────────────┘    └─────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Аутентификация  │
                   │ Rate Limiting   │
                   │ Мониторинг      │
                   │ Load Balancing  │
                   └─────────────────┘
```

---

## 🚀 Быстрый старт

### 1. Запуск системы с Gateway

```bash
# Запуск с Kong API Gateway
python scripts/run_with_gateway.py

# Или вручную через Docker Compose
cd deployment
docker-compose -f kong-gateway.yml up -d
```

### 2. Проверка работы

```bash
# Проверка здоровья через Gateway
curl http://localhost:8080/health

# Получение списка заявок (с JWT)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8080/api/v1/requests
```

---

## 🔧 Архитектура решения

### **До внедрения API Gateway:**
```
┌─────────────┐    ┌─────────────┐
│ Web Client  │───▶│  Backend    │
└─────────────┘    │   :8000     │
┌─────────────┐    │             │
│Mobile Client│───▶│             │
└─────────────┘    └─────────────┘
┌─────────────┐           
│Admin Panel  │───▶ Прямые подключения
└─────────────┘    к backend
```

### **После внедрения API Gateway:**
```
┌─────────────┐    
│ Web Client  │───┐
└─────────────┘   │  ┌─────────────────┐    ┌─────────────┐
┌─────────────┐   ├─▶│   Kong Gateway  │───▶│  Backend    │
│Mobile Client│───┤  │     :8080       │    │   :8000     │
└─────────────┘   │  └─────────────────┘    └─────────────┘
┌─────────────┐   │           │
│Admin Panel  │───┘           ▼
└─────────────┘      ┌─────────────────┐
                     │  Централизованная обработка:
                     │  • Auth & Authorization
                     │  • Rate Limiting
                     │  • Logging & Metrics
                     │  • CORS & Security
                     │  • Load Balancing
                     └─────────────────┘
```

---

## 📋 Основные возможности

### **1. 🛡️ Безопасность**

#### JWT Аутентификация
```yaml
# Автоматическая проверка JWT для защищенных endpoints
protected_routes:
  - /api/v1/requests/*
  - /api/v1/users/*
  - /api/v1/files/*
  - /api/v1/transactions/*

public_routes:
  - /api/v1/auth/*
  - /health
```

#### CORS настройки
```yaml
cors:
  origins:
    - "http://localhost:3000"    # React dev server
    - "https://yourdomain.com"   # Production frontend
  methods: [GET, POST, PUT, DELETE, OPTIONS]
  credentials: true
```

### **2. ⚡ Rate Limiting**

```yaml
rate_limits:
  per_minute: 100     # 100 запросов в минуту
  per_hour: 1000      # 1000 запросов в час
  per_consumer: true  # Индивидуально для каждого клиента
```

### **3. 🔄 Load Balancing**

```yaml
upstream_backend:
  algorithm: round-robin
  health_checks:
    interval: 5s
    path: /health
  targets:
    - backend:8000   # Основной backend
    # - backend2:8000  # Можно добавить дополнительные
```

### **4. 📊 Мониторинг и логирование**

```yaml
monitoring:
  prometheus_metrics: enabled
  request_logging: enabled
  response_times: tracked
  error_rates: tracked
```

---

## 🎮 Управление через Admin API

Kong предоставляет REST API для управления конфигурацией:

### Проверка статуса
```bash
curl http://localhost:8001/status
```

### Просмотр сервисов
```bash
curl http://localhost:8001/services
```

### Просмотр маршрутов
```bash
curl http://localhost:8001/routes
```

### Добавление нового consumer
```bash
curl -X POST http://localhost:8001/consumers \
  -d "username=new-client" \
  -d "custom_id=client-001"
```

### Создание JWT credential
```bash
curl -X POST http://localhost:8001/consumers/new-client/jwt \
  -d "key=client-key" \
  -d "secret=client-secret"
```

---

## 🔍 Мониторинг и метрики

### **Prometheus метрики**

Kong автоматически экспортирует метрики в Prometheus:

```
# Количество запросов
kong_http_requests_total

# Время отклика
kong_request_latency_ms

# Статус коды
kong_http_status

# Пропускная способность
kong_bandwidth_bytes
```

### **Grafana дашборды**

Доступны готовые дашборды для мониторинга:
- Общая производительность API
- Rate limiting статистика  
- Ошибки и статус коды
- Время отклика по endpoints

---

## 📈 Преимущества для твоей системы

### **1. Централизованная безопасность**
```
❌ Раньше: Каждый сервис сам проверяет JWT
✅ Теперь: Kong проверяет все токены централизованно
```

### **2. Единообразное rate limiting**
```
❌ Раньше: Разные ограничения в разных модулях
✅ Теперь: Единые правила для всей системы
```

### **3. Упрощенная маршрутизация**
```
❌ Раньше: Клиенты знают о внутренней структуре API
✅ Теперь: Единый API endpoint для всех клиентов
```

### **4. Масштабируемость**
```
❌ Раньше: Сложно добавлять новые backend инстансы
✅ Теперь: Load balancing "из коробки"
```

---

## 🛠️ Конфигурация для продакшена

### **1. Настройка SSL/TLS**

```yaml
# В kong-gateway.yml добавить SSL сертификаты
kong:
  environment:
    KONG_SSL_CERT: /path/to/cert.pem
    KONG_SSL_CERT_KEY: /path/to/key.pem
  ports:
    - "443:8443"   # HTTPS
```

### **2. База данных для Kong**

Для продакшена рекомендуется PostgreSQL:

```yaml
kong-database:
  image: postgres:13
  environment:
    POSTGRES_DB: kong
    POSTGRES_USER: kong
    POSTGRES_PASSWORD: kong_password
    
kong:
  environment:
    KONG_DATABASE: postgres
    KONG_PG_HOST: kong-database
    KONG_PG_USER: kong
    KONG_PG_PASSWORD: kong_password
```

### **3. Кластер Kong**

```yaml
# Несколько инстансов Kong для высокой доступности
kong-1:
  image: kong:3.4-alpine
  
kong-2:
  image: kong:3.4-alpine
  
# Load balancer перед Kong
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
```

---

## 🚀 Миграция существующих клиентов

### **Поэтапная миграция:**

1. **Фаза 1:** Запуск Kong параллельно
   ```
   Backend API: :8000 (существующие клиенты)
   Kong Gateway: :8080 (новые клиенты)
   ```

2. **Фаза 2:** Переключение клиентов
   ```bash
   # Старый способ
   curl http://localhost:8000/api/v1/requests
   
   # Новый способ
   curl http://localhost:8080/api/v1/requests
   ```

3. **Фаза 3:** Отключение прямого доступа
   ```yaml
   # Закрыть порт 8000 для внешних подключений
   backend:
     ports: []  # Только внутренние подключения
   ```

---

## 🔧 Альтернативные решения

Если Kong не подходит, рассмотри альтернативы:

### **1. Traefik (Рекомендуется для Docker)**
```yaml
traefik:
  image: traefik:v2.9
  command:
    - "--api.insecure=true"
    - "--providers.docker=true"
    - "--entrypoints.web.address=:80"
```

### **2. NGINX Plus**
```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Authorization $http_authorization;
    }
}
```

### **3. AWS API Gateway (для облака)**
```yaml
# Подходит если планируешь деплой в AWS
Resources:
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: BackendAPI
```

---

## 📞 Заключение

**API Gateway с Kong дает твоей системе:**

✅ **Единую точку входа** для всех API  
✅ **Централизованную безопасность** и аутентификацию  
✅ **Автоматический rate limiting** и защиту от DDoS  
✅ **Детальный мониторинг** и метрики  
✅ **Простое масштабирование** backend сервисов  
✅ **Production-ready** конфигурацию из коробки

**Запуск одной командой:**
```bash
python scripts/run_with_gateway.py
```

Твоя система станет более профессиональной, безопасной и готовой к enterprise использованию! 🚀 