#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

def check_request_statuses():
    try:
        engine = create_engine(os.getenv('DATABASE_URL'))
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Получаем уникальные статусы
        result = db.execute(text("SELECT DISTINCT status FROM requests ORDER BY status"))
        statuses = result.fetchall()
        
        print("🔍 СТАТУСЫ В БАЗЕ ДАННЫХ:")
        print("=" * 40)
        
        if statuses:
            for status in statuses:
                status_value = status[0]
                # Подсчитываем количество заявок с каждым статусом
                count_result = db.execute(text("SELECT COUNT(*) FROM requests WHERE status = :status"), {"status": status_value})
                count = count_result.fetchone()[0]
                print(f"✅ '{status_value}' - {count} заявок")
        else:
            print("❌ Нет заявок в базе данных")
            
        # Проверяем общее количество заявок
        total_result = db.execute(text("SELECT COUNT(*) FROM requests"))
        total = total_result.fetchone()[0]
        print("=" * 40)
        print(f"📊 ВСЕГО ЗАЯВОК: {total}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ ОШИБКА: {str(e)}")

if __name__ == "__main__":
    check_request_statuses() 