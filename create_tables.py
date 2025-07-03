#!/usr/bin/env python3
"""
Скрипт для создания всех таблиц в базе данных
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую папку в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.avatar_repository import Base, engine, test_database_connection

async def create_all_tables():
    """Создает все таблицы в базе данных."""
    try:
        print("🔄 Подключение к базе данных...")
        
        # Тестируем подключение
        connection_test = await test_database_connection()
        print(f"✅ {connection_test}")
        
        print("🔄 Создание таблиц...")
        
        # Создаем все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Все таблицы успешно созданы!")
        print("\n📋 Созданные таблицы:")
        print("   - users (пользователи)")
        print("   - avatars (аватары)")
        print("   - animation_projects (проекты анимации)")
        print("   - animation_segments (сегменты анимации)")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False
    finally:
        await engine.dispose()

async def main():
    """Главная функция."""
    print("🚀 Создание таблиц для ToonzyAI...")
    print("-" * 50)
    
    success = await create_all_tables()
    
    print("-" * 50)
    if success:
        print("🎉 Готово! Таблицы созданы и готовы к использованию.")
    else:
        print("💥 Произошла ошибка. Проверьте настройки базы данных.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 