# Правильные URL для доступа к файлам на фронтенде

## Проблема
Фронтенд обращался к файлам по неправильному URL через защищенный эндпоинт, что требовало авторизации.

## Решение
В FastAPI уже настроены статические файлы через `/media` путь в `app/main.py`:

```python
# Подключение статических файлов
if os.path.exists("media"):
    app.mount("/media", StaticFiles(directory="media"), name="media")
```

## Правильные URL для фронтенда

### Файлы БСО
**Правильно:**
```
https://api.lead-schem.ru/media/zayvka/bso/filename.jpg
```

**Неправильно (старый URL):**
```
https://api.lead-schem.ru/api/secure-files/view/zayvka/bso/filename.jpg
```

### Файлы расходных документов
**Правильно:**
```
https://api.lead-schem.ru/media/zayvka/rashod/filename.pdf
```

### Аудиозаписи
**Правильно:**
```
https://api.lead-schem.ru/media/zayvka/zapis/filename.mp3
```

## Структура директорий на сервере
```
/home/deployer/backend-api/media/
├── zayvka/
│   ├── bso/          # Файлы БСО
│   ├── rashod/       # Расходные документы  
│   └── zapis/        # Аудиозаписи
```

## Что нужно изменить на фронтенде
1. Заменить базовый URL для файлов с `/api/secure-files/view` на `/media`
2. Убрать авторизацию для запросов к файлам (они теперь публичные)
3. Использовать простой HTTP GET запрос вместо авторизованного API вызова

**Важно:** Это касается всех типов файлов - БСО, расходных документов И аудиозаписей!

## Пример изменения в коде фронтенда

### Для файлов БСО:
```javascript
// Было:
const fileUrl = `${API_BASE_URL}/api/secure-files/view/zayvka/bso/${filename}`;

// Стало:
const fileUrl = `${API_BASE_URL}/media/zayvka/bso/${filename}`;
```

### Для расходных документов:
```javascript
// Было:
const fileUrl = `${API_BASE_URL}/api/secure-files/view/zayvka/rashod/${filename}`;

// Стало:
const fileUrl = `${API_BASE_URL}/media/zayvka/rashod/${filename}`;
```

### Для аудиозаписей:
```javascript
// Было:
const fileUrl = `${API_BASE_URL}/api/secure-files/view/zayvka/zapis/${filename}`;

// Стало:
const fileUrl = `${API_BASE_URL}/media/zayvka/zapis/${filename}`;
```

## Преимущества нового подхода
- Файлы доступны без авторизации
- Лучшее кеширование браузером
- Меньше нагрузки на API
- Более простая реализация на фронтенде 