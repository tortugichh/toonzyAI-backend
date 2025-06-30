#!/usr/bin/env python3
"""
Тест нового подхода к Veo 2.0 с правильным SDK
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.vertex_ai_client_v2 import generate_video_from_image_v2

async def main():
    print("🚀 Тестирование Veo 2.0 с новым SDK...")
    print("=" * 60)
    
    try:
        # Простой тест без изображения
        prompt = "A magical fantasy forest with glowing plants and floating particles"
        
        print(f"📝 Промпт: {prompt}")
        print("⏳ Генерация видео...")
        
        video_url = await generate_video_from_image_v2(
            start_frame_url=None,  # Без изображения
            animation_prompt=prompt,
            duration_seconds=5
        )
        
        print(f"✅ УСПЕХ! Видео сгенерировано: {video_url}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ОШИБКА: {error_msg}")
        
        # Анализируем тип ошибки
        if "quota" in error_msg.lower():
            print("📊 Это проблема квоты - нужно увеличить лимиты")
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            print("🔐 Это проблема доступа - нужно получить разрешение на Veo")
        elif "not found" in error_msg.lower():
            print("🚫 Модель недоступна - проект не в waitlist")
        elif "billing" in error_msg.lower():
            print("💳 Проблема биллинга - проверьте настройки оплаты")
        else:
            print("🤷 Неизвестная ошибка - проверьте логи")

if __name__ == "__main__":
    asyncio.run(main()) 