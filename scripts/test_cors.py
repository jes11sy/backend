#!/usr/bin/env python3
"""
Скрипт для тестирования CORS настроек
"""
import requests
import sys
from urllib.parse import urljoin

def test_cors(base_url: str, origin: str):
    """Тестирует CORS для указанного origin"""
    print(f"\n🧪 Тестирование CORS для {origin}")
    print(f"📡 API URL: {base_url}")
    
    # Тест preflight запроса
    headers = {
        'Origin': origin,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type,Authorization'
    }
    
    try:
        # OPTIONS запрос (preflight)
        options_url = urljoin(base_url, '/api/v1/health/')
        response = requests.options(options_url, headers=headers, timeout=10)
        
        print(f"📋 OPTIONS запрос статус: {response.status_code}")
        
        # Проверяем CORS заголовки
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
        }
        
        print("\n📊 CORS заголовки:")
        for header, value in cors_headers.items():
            status = "✅" if value else "❌"
            print(f"{status} {header}: {value}")
        
        # Проверяем, разрешен ли наш origin
        allowed_origin = cors_headers['Access-Control-Allow-Origin']
        if allowed_origin == origin or allowed_origin == '*':
            print(f"\n✅ Origin {origin} разрешен!")
            return True
        else:
            print(f"\n❌ Origin {origin} НЕ разрешен!")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def main():
    """Основная функция"""
    # Настройки по умолчанию
    base_url = "https://api.lead-schem.ru"
    origins_to_test = [
        "https://lead-schem.ru",
        "https://www.lead-schem.ru",
        "https://admin.lead-schem.ru",
        "http://localhost:3000",  # для разработки
    ]
    
    # Если передан аргумент, используем его как URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🚀 Тестирование CORS для API: {base_url}")
    print("=" * 50)
    
    results = {}
    for origin in origins_to_test:
        results[origin] = test_cors(base_url, origin)
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📈 ИТОГОВЫЙ ОТЧЕТ:")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    for origin, success in results.items():
        status = "✅ РАБОТАЕТ" if success else "❌ НЕ РАБОТАЕТ"
        print(f"{status} {origin}")
    
    print(f"\n📊 Результат: {success_count}/{total_count} origins настроены правильно")
    
    if success_count == total_count:
        print("🎉 Все CORS настройки работают корректно!")
        sys.exit(0)
    else:
        print("⚠️  Есть проблемы с CORS настройками!")
        sys.exit(1)

if __name__ == "__main__":
    main() 