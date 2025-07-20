# Настройка CORS для фронтенда

## Обзор

В этом проекте CORS настраивается через переменные окружения в GitLab CI/CD для автоматического деплоя.

## Текущая настройка

### Для домена lead-schem.ru

CORS уже настроен для следующих доменов:
- `https://lead-schem.ru`
- `https://www.lead-schem.ru` 
- `https://admin.lead-schem.ru`

## Настройка в GitLab CI/CD

### 1. Добавление переменной CORS_ORIGINS

В GitLab перейдите в:
**Settings → CI/CD → Variables**

Добавьте переменную:
- **Key**: `CORS_ORIGINS`
- **Value**: `https://lead-schem.ru,https://www.lead-schem.ru,https://admin.lead-schem.ru`
- **Type**: Variable
- **Environment scope**: All (или production)
- **Protect variable**: ✅ 
- **Mask variable**: ❌

### 2. Переменная автоматически используется

GitLab CI/CD автоматически передает эту переменную в контейнер при деплое.

## Как это работает

1. **config.py** читает переменную `CORS_ORIGINS` или `ALLOWED_ORIGINS`
2. **main.py** использует `settings.get_allowed_origins` для настройки CORS middleware
3. При деплое GitLab передает переменную в контейнер

## Тестирование CORS

Используйте скрипт для проверки:

```bash
python scripts/test_cors.py
```

Или с кастомным URL:
```bash
python scripts/test_cors.py https://api.lead-schem.ru
```

## Для разработки

Если работаете локально, создайте `.env` файл:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://lead-schem.ru
```

## Добавление нового домена

1. Обновите переменную `CORS_ORIGINS` в GitLab CI/CD Variables
2. Добавьте домен через запятую: `существующие_домены,новый_домен`
3. Сделайте коммит для запуска деплоя
4. Проверьте работу через скрипт тестирования

## Структура кода

```
app/
├── core/
│   └── config.py          # Чтение CORS_ORIGINS
├── main.py                # Настройка CORS middleware
└── api/
    └── auth.py            # CORS заголовки в ответах

scripts/
└── test_cors.py           # Тестирование CORS

.gitlab-ci.yml             # Передача переменных в контейнер
```

## Отладка

### Проверка переменных в контейнере

```bash
# Подключиться к контейнеру
docker exec -it backend_app_1 bash

# Проверить переменную
echo $CORS_ORIGINS
```

### Логи CORS в приложении

Проверьте логи приложения на наличие CORS ошибок:

```bash
docker logs backend_app_1 | grep -i cors
```

### Проверка заголовков в браузере

1. Откройте DevTools (F12)
2. Перейдите на вкладку Network
3. Сделайте запрос к API
4. Проверьте заголовки ответа:
   - `Access-Control-Allow-Origin`
   - `Access-Control-Allow-Methods`
   - `Access-Control-Allow-Headers`
   - `Access-Control-Allow-Credentials`

## Troubleshooting

### Проблема: CORS ошибка в браузере

**Решение:**
1. Проверьте, что домен добавлен в `CORS_ORIGINS`
2. Убедитесь, что протокол правильный (http/https)
3. Перезапустите контейнеры после изменения переменных

### Проблема: OPTIONS запрос не работает

**Решение:**
1. Проверьте, что роуты обрабатывают OPTIONS
2. Убедитесь, что CORS middleware добавлен первым в `main.py`

### Проблема: Localhost работает, продакшен нет

**Решение:**
1. Проверьте переменную `CORS_ORIGINS` в GitLab CI/CD
2. Убедитесь, что используется правильный протокол (https)
3. Проверьте SSL сертификаты 