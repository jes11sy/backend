# 🚀 НАСТРОЙКА GITLAB CI/CD ДЛЯ ПОДКЛЮЧЕНИЯ К СЕРВЕРУ

## 📋 **ЧТО НУЖНО СДЕЛАТЬ:**

### **1. 🔑 SSH КЛЮЧИ УЖЕ СОЗДАНЫ**

**Публичный ключ (для сервера):**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPi266mWGNdEQIhFyD0MbhHxLm1h/gOWlgNi93AcvJ2m gitlab-ci@api.lead-schem.ru
```

**Приватный ключ (для GitLab):**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACD4tuuplhjXRECIRcg9DG4R8S5tYf4DlpYDYvdwHLydpgAAAKDU1TqK1NU6
igAAAAtzc2gtZWQyNTUxOQAAACD4tuuplhjXRECIRcg9DG4R8S5tYf4DlpYDYvdwHLydpg
AAAEDb/W7GzqZmszkspA7jH87UGNeo2iY7F5EMChsNjL2TIPi266mWGNdEQIhFyD0MbhHx
Lm1h/gOWlgNi93AcvJ2mAAAAG2dpdGxhYi1jaUBhcGkubGVhZC1zY2hlbS5ydQEC
-----END OPENSSH PRIVATE KEY-----
```

---

## 🖥️ **НАСТРОЙКА СЕРВЕРА**

### **Шаг 1: Подключись к серверу**
```bash
ssh root@176.124.200.32
# Пароль: gG9h2CW3SdYs-g
```

### **Шаг 2: Создай пользователя для деплоя**
```bash
# Создание пользователя
sudo adduser deployer

# Добавление в группу sudo (если нужны права администратора)
sudo usermod -aG sudo deployer

# Создание директории для SSH ключей
sudo mkdir -p /home/deployer/.ssh
sudo chmod 700 /home/deployer/.ssh
```

### **Шаг 3: Добавь публичный ключ GitLab на сервер**
```bash
# Добавь публичный ключ в authorized_keys
sudo nano /home/deployer/.ssh/authorized_keys

# Вставь в файл:
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPi266mWGNdEQIhFyD0MbhHxLm1h/gOWlgNi93AcvJ2m gitlab-ci@api.lead-schem.ru

# Установи правильные права
sudo chmod 600 /home/deployer/.ssh/authorized_keys
sudo chown -R deployer:deployer /home/deployer/.ssh
```

### **Шаг 4: Установи Docker на сервер**
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя deployer в группу docker
sudo usermod -aG docker deployer

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### **Шаг 5: Создай структуру проекта**
```bash
# Переключись на пользователя deployer
sudo su - deployer

# Создай директории
mkdir -p ~/backend-api
mkdir -p ~/backend-api/backups
mkdir -p ~/backend-api/logs
mkdir -p ~/backend-api/ssl

# Создай файл окружения (будет обновляться через CI/CD)
touch ~/backend-api/.env
```

---

## 🦊 **НАСТРОЙКА GITLAB CI/CD ПЕРЕМЕННЫХ**

### **В GitLab добавь дополнительные переменные:**

**🖥️ Серверные переменные:**
- `PRODUCTION_HOST` = `176.124.200.32`
- `PRODUCTION_USER` = `deployer`
- `PRODUCTION_SSH_PRIVATE_KEY` = `[весь приватный ключ выше]`

**🔒 SSL/Cloudflare (ВАЖНО!):**
- `CLOUDFLARE_DNS_API_TOKEN` = `[твой Cloudflare API токен]`

### **Как получить Cloudflare API токен:**

1. Зайди на [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. **My Profile** → **API Tokens** → **Create Token**
3. **Custom token**:
   - **Token name:** `gitlab-ci-lead-schem`
   - **Permissions:** 
     - `Zone:DNS:Edit`
     - `Zone:Zone:Read`
   - **Zone Resources:** 
     - `Include: Specific zone: lead-schem.ru`
4. Скопируй токен и добавь в GitLab Variables

---

## ⚙️ **КАК РАБОТАЕТ ДЕПЛОЙ:**

### **🔄 Процесс автоматического деплоя:**

1. **Push в GitLab** → запускается CI/CD
2. **Тестирование** → проверка кода
3. **Сборка Docker образа** → создание контейнера
4. **Подключение к серверу** → SSH через GitLab Runner
5. **Обновление кода** → git pull на сервере
6. **Перезапуск сервисов** → docker-compose up
7. **Уведомления** → в Telegram

### **🚀 Что будет развернуто:**

- ✅ **Kong API Gateway** (порт 8000, 8443)
- ✅ **FastAPI Backend** (внутренний порт)
- ✅ **Redis** (кеширование)
- ✅ **Traefik** (SSL прокси)
- ✅ **Prometheus + Grafana** (мониторинг)
- ✅ **SSL сертификаты** (Let's Encrypt)

---

## 🔧 **ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ**

### **Проверь SSH подключение:**
```bash
# С твоего компьютера
ssh -i gitlab_deploy_key deployer@176.124.200.32

# Если подключение успешно, то GitLab тоже сможет подключиться
```

---

## ⚠️ **ВАЖНЫЕ МОМЕНТЫ:**

1. **🔐 Безопасность:**
   - Приватный ключ только в GitLab Variables (Protected + Masked)
   - Публичный ключ только на сервере

2. **🌐 DNS настройки:**
   - `api.lead-schem.ru` должен указывать на IP `176.124.200.32`
   - Cloudflare Proxy должен быть выключен для настройки SSL (серая тучка ☁️)

3. **🚀 Первый деплой:**
   - CI/CD автоматически склонирует репозиторий на сервер
   - Создаст все необходимые Docker контейнеры
   - Настроит SSL сертификаты

---

## 📞 **СЛЕДУЮЩИЕ ШАГИ:**

1. ✅ **Настрой сервер** (выше)
2. ✅ **Добавь SSH ключ** на сервер
3. ✅ **Получи Cloudflare API токен**
4. ✅ **Добавь переменные** в GitLab
5. ✅ **Сделай git push** → запустится автодеплой!

**Готово к настройке сервера?** 🎯 