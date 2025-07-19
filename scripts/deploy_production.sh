#!/bin/bash

# ============================================
# PRODUCTION DEPLOYMENT SCRIPT
# Скрипт для деплоя на api.lead-schem.ru
# ============================================

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Логирование
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Проверка переменных окружения
check_env_vars() {
    log "Проверка переменных окружения..."
    
    required_vars=(
        "PRODUCTION_HOST"
        "PRODUCTION_USER"
        "CI_REGISTRY_IMAGE"
        "POSTGRESQL_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Переменная окружения $var не установлена!"
        fi
    done
    
    log "✅ Все необходимые переменные установлены"
}

# Проверка подключения к серверу
check_server_connection() {
    log "Проверка подключения к серверу $PRODUCTION_HOST..."
    
    if ! ssh -o ConnectTimeout=10 "$PRODUCTION_USER@$PRODUCTION_HOST" "echo 'Connection successful'"; then
        error "Не удалось подключиться к серверу $PRODUCTION_HOST"
    fi
    
    log "✅ Подключение к серверу успешно"
}

# Создание резервной копии
create_backup() {
    log "Создание резервной копии..."
    
    ssh "$PRODUCTION_USER@$PRODUCTION_HOST" << 'EOF'
        cd /opt/backend
        
        # Создание директории для бэкапов
        mkdir -p /opt/backups/$(date +%Y-%m-%d)
        
        # Бэкап базы данных (внешней)
        # Используется pg_dump для подключения к внешней БД
        PGPASSWORD=$POSTGRESQL_PASSWORD pg_dump \
            -h $POSTGRESQL_HOST \
            -p $POSTGRESQL_PORT \
            -U $POSTGRESQL_USER \
            -d $POSTGRESQL_DBNAME \
            > /opt/backups/$(date +%Y-%m-%d)/database_backup.sql
        
        # Бэкап файлов
        tar -czf /opt/backups/$(date +%Y-%m-%d)/media_backup.tar.gz \
            -C /opt/backend media/
        
        # Сохранение текущего docker-compose файла
        cp docker-compose.production.yml \
            /opt/backups/$(date +%Y-%m-%d)/docker-compose.backup.yml
        
        echo "✅ Резервная копия создана"
EOF
    
    log "✅ Резервная копия создана"
}

# Деплой приложения
deploy_application() {
    log "Начало деплоя приложения..."
    
    # Загрузка переменных окружения на сервер
    scp deployment/env.production.example "$PRODUCTION_USER@$PRODUCTION_HOST:/opt/backend/.env.production"
    
    # Выполнение деплоя на сервере
    ssh "$PRODUCTION_USER@$PRODUCTION_HOST" << EOF
        cd /opt/backend
        
        # Обновление кода
        git pull origin main
        
        # Логин в Docker Registry
        echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
        
        # Загрузка новых образов
        docker-compose -f docker-compose.production.yml pull backend
        
        # Создание тега для отката
        docker tag \$(docker images $CI_REGISTRY_IMAGE/backend:latest -q | head -1) \
            $CI_REGISTRY_IMAGE/backend:previous || true
        
        # Остановка старых контейнеров
        docker-compose -f docker-compose.production.yml down
        
        # Запуск новых контейнеров
        docker-compose -f docker-compose.production.yml up -d
        
        # Ожидание запуска
        sleep 30
        
        # Проверка здоровья
        if ! curl -f https://api.lead-schem.ru/health; then
            echo "❌ Health check failed, rolling back..."
            docker-compose -f docker-compose.production.yml down
            docker tag $CI_REGISTRY_IMAGE/backend:previous $CI_REGISTRY_IMAGE/backend:latest
            docker-compose -f docker-compose.production.yml up -d
            exit 1
        fi
        
        # Очистка старых образов
        docker system prune -f
        
        echo "✅ Деплой завершен успешно"
EOF
    
    log "✅ Деплой приложения завершен"
}

# Проверка состояния после деплоя
post_deploy_checks() {
    log "Проверка состояния после деплоя..."
    
    # Проверка доступности API
    if curl -f https://api.lead-schem.ru/health; then
        log "✅ API доступен"
    else
        error "❌ API недоступен"
    fi
    
    # Проверка состояния контейнеров
    ssh "$PRODUCTION_USER@$PRODUCTION_HOST" << 'EOF'
        cd /opt/backend
        
        echo "Состояние контейнеров:"
        docker-compose -f docker-compose.production.yml ps
        
        echo "Использование ресурсов:"
        docker stats --no-stream
        
        echo "Логи приложения:"
        docker-compose -f docker-compose.production.yml logs --tail=20 backend
EOF
    
    log "✅ Проверки завершены"
}

# Отправка уведомления
send_notification() {
    local status=$1
    local message=$2
    
    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
        curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -H "Content-Type: application/json" \
            -d "{
                \"chat_id\": \"$TELEGRAM_CHAT_ID\",
                \"text\": \"$status Деплой на api.lead-schem.ru\n\n$message\n\n⏰ $(date)\",
                \"parse_mode\": \"HTML\"
            }" > /dev/null 2>&1
    fi
}

# Главная функция
main() {
    log "🚀 Начало деплоя на продакшен сервер api.lead-schem.ru"
    
    # Проверки перед деплоем
    check_env_vars
    check_server_connection
    
    # Создание резервной копии
    create_backup
    
    # Деплой
    if deploy_application; then
        post_deploy_checks
        send_notification "✅" "Деплой завершен успешно!"
        log "🎉 Деплой завершен успешно!"
    else
        send_notification "❌" "Ошибка деплоя!"
        error "❌ Ошибка во время деплоя"
    fi
}

# Проверка аргументов
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Использование: $0 [options]"
    echo ""
    echo "Опции:"
    echo "  --help, -h     Показать эту справку"
    echo "  --dry-run      Проверить настройки без деплоя"
    echo ""
    echo "Переменные окружения:"
    echo "  PRODUCTION_HOST     Хост продакшен сервера"
    echo "  PRODUCTION_USER     Пользователь для SSH"
    echo "  CI_REGISTRY_IMAGE   Docker registry образа"
    echo "  TELEGRAM_BOT_TOKEN  Токен бота для уведомлений"
    echo "  TELEGRAM_CHAT_ID    ID чата для уведомлений"
    exit 0
fi

if [[ "$1" == "--dry-run" ]]; then
    log "🔍 Dry run mode - проверка настроек"
    check_env_vars
    check_server_connection
    log "✅ Настройки корректны"
    exit 0
fi

# Запуск деплоя
main "$@" 