#!/usr/bin/env python3
"""
Скрипт для проверки CORS на продакшен сервере
"""
import requests
import json

def check_server_status():
    """Проверяет статус сервера и конфигурацию"""
    base_url = "https://api.lead-schem.ru"
    
    print("🔍 Проверка сервера API...")
    
    # Проверяем health endpoint
    try:
        health_response = requests.get(f"{base_url}/api/v1/health/", timeout=10)
        print(f"✅ Health check: {health_response.status_code}")
        if health_response.status_code == 200:
            print(f"📊 Response: {health_response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Проверяем CORS для разных endpoints
    origins_to_test = ["https://lead-schem.ru", "http://localhost:3000"]
    endpoints_to_test = [
        "/api/v1/auth/login",
        "/api/v1/health/", 
        "/api/auth/login",  # старый endpoint
    ]
    
    for origin in origins_to_test:
        print(f"\n🧪 Тестирование origin: {origin}")
        
        for endpoint in endpoints_to_test:
            print(f"  📡 Endpoint: {endpoint}")
            
            # OPTIONS preflight запрос
            headers = {
                'Origin': origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,Authorization'
            }
            
            try:
                url = f"{base_url}{endpoint}"
                response = requests.options(url, headers=headers, timeout=10)
                
                print(f"    📋 Status: {response.status_code}")
                
                # Проверяем CORS заголовки
                cors_headers = [
                    'Access-Control-Allow-Origin',
                    'Access-Control-Allow-Methods', 
                    'Access-Control-Allow-Headers',
                    'Access-Control-Allow-Credentials'
                ]
                
                for header in cors_headers:
                    value = response.headers.get(header)
                    status = "✅" if value else "❌"
                    print(f"    {status} {header}: {value}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")

def check_real_browser_request():
    """Имитирует реальный браузерный запрос"""
    print("\n🌐 Имитация браузерного запроса...")
    
    # Сначала OPTIONS (preflight)
    headers = {
        'Origin': 'https://lead-schem.ru',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type,authorization',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        url = "https://api.lead-schem.ru/api/v1/auth/login"
        preflight = requests.options(url, headers=headers, timeout=10)
        
        print(f"📋 Preflight status: {preflight.status_code}")
        print("📊 Preflight headers:")
        for key, value in preflight.headers.items():
            if 'access-control' in key.lower():
                print(f"   {key}: {value}")
                
        # Потом POST запрос
        if preflight.status_code == 200:
            post_headers = {
                'Origin': 'https://lead-schem.ru',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            post_data = {"username": "test", "password": "test"}
            
            post_response = requests.post(url, 
                                        headers=post_headers, 
                                        json=post_data, 
                                        timeout=10)
                                        
            print(f"\n📮 POST status: {post_response.status_code}")
            print("📊 POST CORS headers:")
            for key, value in post_response.headers.items():
                if 'access-control' in key.lower():
                    print(f"   {key}: {value}")
                    
    except Exception as e:
        print(f"❌ Browser request failed: {e}")

if __name__ == "__main__":
    check_server_status()
    check_real_browser_request() 