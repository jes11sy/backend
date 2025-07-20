# Полная инструкция по API и структуре файлов

## Содержание
1. [Базовая информация API](#базовая-информация-api)
2. [Аутентификация](#аутентификация)
3. [Структура файлов](#структура-файлов)
4. [API эндпоинты](#api-эндпоинты)
5. [Загрузка файлов](#загрузка-файлов)
6. [Доступ к файлам](#доступ-к-файлам)
7. [Webhook Mango](#webhook-mango)
8. [Мониторинг и метрики](#мониторинг-и-метрики)
9. [Примеры использования](#примеры-использования)

## Базовая информация API

### Базовые URL
- **Production**: `https://api.lead-schem.ru`
- **Development**: `http://localhost:8000`

### Формат ответов
Все ответы возвращаются в формате JSON:
```json
{
  "id": 1,
  "status": "success",
  "data": {...},
  "timestamp": "2025-01-15T15:00:00Z"
}
```

### Коды ошибок
- `200` - Успешно
- `400` - Ошибка валидации
- `401` - Не авторизован
- `403` - Нет доступа
- `404` - Не найдено
- `429` - Превышен лимит запросов
- `500` - Ошибка сервера

## Аутентификация

### Получение токена
```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

### Использование токена
```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

### Проверка токена
```bash
GET /api/auth/me
Authorization: Bearer YOUR_JWT_TOKEN
```

## Структура файлов

### Директории на сервере
```
/home/deployer/backend-api/media/
├── zayvka/                 # Файлы заявок
│   ├── bso/               # БСО документы
│   ├── rashod/            # Расходные документы
│   └── zapis/             # Аудиозаписи звонков
└── gorod/                 # Файлы городских транзакций
    └── rashod/            # Расходные документы
```

### URL для доступа к файлам
```
https://api.lead-schem.ru/media/{path}

Примеры:
- https://api.lead-schem.ru/media/zayvka/bso/filename.jpg
- https://api.lead-schem.ru/media/zayvka/rashod/filename.pdf
- https://api.lead-schem.ru/media/zayvka/zapis/filename.mp3
- https://api.lead-schem.ru/media/gorod/rashod/filename.pdf
```

## API эндпоинты

### 1. Заявки (Requests)

#### Получить список заявок
```bash
GET /api/requests
Authorization: Bearer TOKEN
```

#### Создать заявку
```bash
POST /api/requests
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "advertising_campaign_id": 1,
  "city_id": 1,
  "request_type_id": 1,
  "client_phone": "+79123456789",
  "client_name": "Иван Иванов",
  "address": "ул. Примерная, 123"
}
```

#### Получить заявку по ID
```bash
GET /api/requests/{request_id}
Authorization: Bearer TOKEN
```

#### Обновить заявку
```bash
PUT /api/requests/{request_id}
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "status": "В работе",
  "master_id": 1
}
```

### 2. Транзакции (Transactions)

#### Получить список транзакций
```bash
GET /api/transactions
Authorization: Bearer TOKEN
```

#### Создать транзакцию
```bash
POST /api/transactions
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "city_id": 1,
  "transaction_type_id": 1,
  "amount": 1500.00,
  "notes": "Комиссия за сделку"
}
```

### 3. Пользователи (Users)

#### Получить список мастеров
```bash
GET /api/masters
Authorization: Bearer TOKEN
```

#### Получить список сотрудников
```bash
GET /api/employees
Authorization: Bearer TOKEN
```

## Загрузка файлов

### 1. БСО к заявке
```bash
POST /api/requests/{request_id}/upload-bso/
Content-Type: multipart/form-data
Authorization: Bearer TOKEN

file: [файл.jpg/png/pdf/doc/docx]
```

**Поддерживаемые форматы**: `.jpg`, `.jpeg`, `.png`, `.pdf`, `.doc`, `.docx`

### 2. Расходный документ к заявке
```bash
POST /api/requests/{request_id}/upload-expense/
Content-Type: multipart/form-data
Authorization: Bearer TOKEN

file: [файл.jpg/png/pdf/doc/docx]
```

### 3. Аудиозапись к заявке
```bash
POST /api/requests/{request_id}/upload-recording/
Content-Type: multipart/form-data
Authorization: Bearer TOKEN

file: [файл.mp3/wav/ogg/m4a/amr]
```

**Поддерживаемые форматы**: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.amr`

### 4. Файл к транзакции
```bash
POST /api/transactions/{transaction_id}/upload-file/
Content-Type: multipart/form-data
Authorization: Bearer TOKEN

file: [файл]
```

### Ответ при загрузке файла
```json
{
  "file_path": "media/zayvka/bso/uuid-filename.jpg"
}
```

## Доступ к файлам

### Публичный доступ (рекомендуется)
Файлы доступны напрямую через статические URL без авторизации:
```
https://api.lead-schem.ru/media/zayvka/bso/filename.jpg
https://api.lead-schem.ru/media/zayvka/rashod/filename.pdf
https://api.lead-schem.ru/media/zayvka/zapis/filename.mp3
```

### Защищенный доступ (с авторизацией)
```bash
GET /api/secure-files/view/{file_path}
Authorization: Bearer TOKEN

GET /api/secure-files/download/{file_path}
Authorization: Bearer TOKEN
```

## Webhook Mango

### Настройка webhook
URL для настройки в панели Mango Office:
```
https://api.lead-schem.ru/api/webhook/mango
```

### Безопасность
- Проверка IP адресов (настраивается в `MANGO_ALLOWED_IPS`)
- Проверка подписи (настраивается в `MANGO_WEBHOOK_SECRET`)

### Формат webhook
```json
{
  "call_id": "12345",
  "from": {"number": "79123456789"},
  "to": {"number": "79987654321", "line_number": "79987654321"},
  "call_state": "Disconnected"
}
```

## Мониторинг и метрики

### Здоровье системы
```bash
GET /api/health
GET /api/health/database
GET /api/health/ready
```

### Метрики Prometheus
```bash
GET /metrics/prometheus
```

### Статус записей звонков
```bash
GET /api/recordings/status
Authorization: Bearer TOKEN
```

### Ручная загрузка записей
```bash
POST /api/recordings/download
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "days_back": 7
}
```

## Примеры использования

### JavaScript/TypeScript

#### Загрузка файла БСО
```javascript
const uploadBSO = async (requestId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`https://api.lead-schem.ru/api/requests/${requestId}/upload-bso/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return response.json();
};
```

#### Отображение загруженного файла
```javascript
const showFile = (filePath) => {
  // Используем прямую ссылку на статический файл
  const fileUrl = `https://api.lead-schem.ru/${filePath}`;
  
  // Для изображений
  const img = document.createElement('img');
  img.src = fileUrl;
  
  // Для ссылки на скачивание
  const link = document.createElement('a');
  link.href = fileUrl;
  link.target = '_blank';
  link.textContent = 'Скачать файл';
};
```

#### Создание заявки
```javascript
const createRequest = async (requestData) => {
  const response = await fetch('https://api.lead-schem.ru/api/requests', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(requestData)
  });
  
  return response.json();
};
```

### Python

#### Загрузка файла
```python
import requests

def upload_file(request_id, file_path, token):
    url = f"https://api.lead-schem.ru/api/requests/{request_id}/upload-bso/"
    
    with open(file_path, 'rb') as file:
        files = {'file': file}
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.post(url, files=files, headers=headers)
        return response.json()
```

#### Получение списка заявок
```python
def get_requests(token):
    url = "https://api.lead-schem.ru/api/requests"
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(url, headers=headers)
    return response.json()
```

### cURL

#### Аутентификация
```bash
curl -X POST "https://api.lead-schem.ru/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

#### Загрузка файла
```bash
curl -X POST "https://api.lead-schem.ru/api/requests/1/upload-bso/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/file.jpg"
```

#### Получение заявок
```bash
curl -X GET "https://api.lead-schem.ru/api/requests" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Лимиты и ограничения

### Размеры файлов
- Максимальный размер файла: **10 MB**
- Максимальное количество файлов на пользователя: **100**

### Rate Limiting
- Максимум запросов в минуту: **100** (настраивается)
- Максимум попыток входа в час: **5**

### Безопасность
- Все файлы проверяются на безопасность
- Запрещены исполняемые файлы (.exe, .bat, .php и т.д.)
- Проверка MIME типов и магических байтов

## Версионирование API

### Доступные версии
- **v1**: `/api/v1/` - стабильная версия
- **v2**: `/api/v2/` - бета версия с расширенными возможностями

### Заголовок версии
```
API-Version: 1.0
```

### Обратная совместимость
Эндпоинты без версии автоматически направляются в v1:
```
/api/requests → /api/v1/requests
```

## Техническая поддержка

### Логи
Все действия логируются. Для отладки используйте:
```bash
docker logs backend-production | grep ERROR
```

### Документация API
- Swagger UI: `https://api.lead-schem.ru/docs`
- ReDoc: `https://api.lead-schem.ru/redoc`
- OpenAPI схема: `https://api.lead-schem.ru/openapi.json`

### Контакты
- Разработчик: `your-email@example.com`
- Репозиторий: `https://gitlab.com/jes11sy-group/backend` 