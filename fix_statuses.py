#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv
import psycopg2

# Загружаем переменные окружения
load_dotenv()

def fix_statuses():
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(
            host=os.getenv('POSTGRESQL_HOST', 'localhost'),
            port=os.getenv('POSTGRESQL_PORT', 5432),
            user=os.getenv('POSTGRESQL_USER'),
            password=os.getenv('POSTGRESQL_PASSWORD'),
            database=os.getenv('POSTGRESQL_DBNAME')
        )
        
        cur = conn.cursor()
        
        print("🔧 ОБНОВЛЯЕМ СТАТУСЫ НА РУССКИЙ ЯЗЫК...")
        print("=" * 50)
        
        # Обновляем статусы
        status_updates = [
            ("new", "Новая"),
            ("pending", "Ожидает"),
            ("in_progress", "В работе"),
            ("done", "Готово"),
            ("completed", "Готово"),
            ("cancelled", "Отказ"),
            ("assigned", "Принял"),
            ("accepted", "Принял"),
            ("in_way", "В пути"),
            ("in_work", "В работе"),
            ("waiting", "Ожидает принятия"),
            ("recall", "Перезвонить"),
            ("tno", "ТНО"),
            ("refused", "Отказ"),
            ("finished", "Готово")
        ]
        
        total_updated = 0
        
        for old_status, new_status in status_updates:
            cur.execute("UPDATE requests SET status = %s WHERE status = %s", (new_status, old_status))
            updated_count = cur.rowcount
            if updated_count > 0:
                print(f"✅ '{old_status}' → '{new_status}': {updated_count} заявок")
                total_updated += updated_count
        
        # Проверяем результат
        cur.execute("SELECT DISTINCT status, COUNT(*) FROM requests GROUP BY status ORDER BY status")
        results = cur.fetchall()
        
        print("=" * 50)
        print("📊 ИТОГОВЫЕ СТАТУСЫ:")
        for status, count in results:
            print(f"   {status}: {count} заявок")
        
        print("=" * 50)
        print(f"🎉 ОБНОВЛЕНО ВСЕГО: {total_updated} заявок")
        
        # Подтверждаем изменения
        conn.commit()
        
        cur.close()
        conn.close()
        
        print("✅ ГОТОВО! Статусы обновлены на русский язык.")
        
    except Exception as e:
        print(f"❌ ОШИБКА: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    fix_statuses() 