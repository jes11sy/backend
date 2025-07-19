#!/usr/bin/env python3
"""
Скрипт для запуска backend системы с Kong API Gateway
"""

import subprocess
import sys
import time
import requests
import os
from pathlib import Path

def run_command(command, cwd=None, shell=True):
    """Выполнение команды с обработкой ошибок"""
    try:
        result = subprocess.run(
            command, 
            shell=shell, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения команды: {command}")
        print(f"Код ошибки: {e.returncode}")
        print(f"Stderr: {e.stderr}")
        return False, e.stderr

def check_service(url, service_name, timeout=30):
    """Проверка доступности сервиса"""
    print(f"🔍 Проверяю доступность {service_name}...")
    
    for i in range(timeout):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {service_name} доступен!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < timeout - 1:
            print(f"⏳ Ожидание {service_name}... ({i+1}/{timeout})")
            time.sleep(1)
    
    print(f"❌ {service_name} недоступен после {timeout} секунд")
    return False

def main():
    """Основная функция запуска"""
    print("🚀 Запуск системы с Kong API Gateway...")
    
    # Проверяем наличие Docker
    success, _ = run_command("docker --version")
    if not success:
        print("❌ Docker не установлен или недоступен")
        sys.exit(1)
    
    # Проверяем наличие docker-compose
    success, _ = run_command("docker-compose --version")
    if not success:
        print("❌ Docker Compose не установлен или недоступен")
        sys.exit(1)
    
    # Переходим в директорию deployment
    deployment_dir = Path(__file__).parent.parent / "deployment"
    
    print("🔧 Останавливаю существующие контейнеры...")
    run_command("docker-compose -f kong-gateway.yml down", cwd=deployment_dir)
    
    print("🏗️ Собираю и запускаю сервисы...")
    success, output = run_command(
        "docker-compose -f kong-gateway.yml up -d --build", 
        cwd=deployment_dir
    )
    
    if not success:
        print("❌ Ошибка запуска сервисов")
        print(output)
        sys.exit(1)
    
    print("✅ Сервисы запущены! Проверяю доступность...")
    
    # Проверяем сервисы
    services = [
        ("http://localhost:8000/health", "Backend API"),
        ("http://localhost:6379", "Redis", False),  # Redis не имеет HTTP endpoint
        ("http://localhost:8080/health", "Kong API Gateway"),
        ("http://localhost:9090", "Prometheus"),
        ("http://localhost:3001", "Grafana")
    ]
    
    all_healthy = True
    for service_info in services:
        if len(service_info) == 2:
            url, name = service_info
            if not check_service(url, name):
                all_healthy = False
        else:
            # Для Redis просто пропускаем проверку
            print(f"⏭️ Пропускаю проверку {service_info[1]}")
    
    print("\n" + "="*60)
    if all_healthy:
        print("🎉 Система успешно запущена!")
    else:
        print("⚠️ Некоторые сервисы могут быть недоступны")
    
    print("\n📋 Доступные сервисы:")
    print("🌐 Kong API Gateway:     http://localhost:8080")
    print("🔧 Kong Admin API:       http://localhost:8001")
    print("⚡ Backend API (прямой): http://localhost:8000")
    print("📊 Prometheus:           http://localhost:9090")
    print("📈 Grafana:              http://localhost:3001")
    print("📚 API Docs:             http://localhost:8080/docs")
    print("📖 ReDoc:                http://localhost:8080/redoc")
    
    print("\n🔑 Примеры API запросов через Gateway:")
    print("GET  http://localhost:8080/api/v1/requests")
    print("GET  http://localhost:8080/api/v1/users") 
    print("POST http://localhost:8080/api/v1/auth/login")
    print("GET  http://localhost:8080/health")
    
    print("\n⚠️ Внимание:")
    print("- Все API запросы теперь идут через порт 8080 (Kong)")
    print("- Для защищенных endpoints нужна JWT аутентификация")
    print("- Rate limiting: 100 запросов/мин, 1000 запросов/час")
    
    print("\n🛑 Для остановки используйте:")
    print("docker-compose -f deployment/kong-gateway.yml down")
    print("="*60)

if __name__ == "__main__":
    main() 