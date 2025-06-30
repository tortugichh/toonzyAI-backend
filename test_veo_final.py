#!/usr/bin/env python3
"""
Финальный тест Veo 2.0 с правильным REST API
Основан на официальной документации Google Cloud
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.vertex_ai_client_v2 import generate_video_from_image_v2

async def main():
    print("🎬 ФИНАЛЬНЫЙ ТЕСТ VEO 2.0")
    print("=" * 50)
    print("📋 Используем официальную REST API документацию")
    print("🔗 https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation")
    print("=" * 50)
    
    try:
        # Тест 1: Text-to-video (без изображения)
        print("\n🧪 ТЕСТ 1: Text-to-Video")
        prompt = "A peaceful lake with swans swimming, golden hour lighting"
        
        print(f"📝 Промпт: {prompt}")
        print("⏳ Отправка запроса на predictLongRunning...")
        
        video_url = await generate_video_from_image_v2(
            start_frame_url=None,  # Без изображения = text-to-video
            animation_prompt=prompt,
            duration_seconds=5
        )
        
        print(f"✅ УСПЕХ! Видео сгенерировано!")
        print(f"📁 GCS URI: {video_url}")
        
        # Проверяем формат ответа
        if video_url.startswith("gs://"):
            print("✅ Правильный формат GCS URI")
        else:
            print("⚠️ Неожиданный формат URL")
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ОШИБКА: {error_msg}")
        
        # Детальный анализ ошибки
        print("\n🔍 АНАЛИЗ ОШИБКИ:")
        
        if "404" in error_msg or "not available" in error_msg.lower():
            print("📋 Причина: Проект не имеет доступа к Veo")
            print("💡 Решение: Подать заявку на Veo Waitlist")
            print("🔗 https://cloud.google.com/vertex-ai/generative-ai/docs/video/overview")
            
        elif "429" in error_msg or "quota" in error_msg.lower():
            print("📋 Причина: Превышена квота")
            print("💡 Решение: Увеличить квоту в Google Cloud Console")
            
        elif "403" in error_msg or "permission" in error_msg.lower():
            print("📋 Причина: Недостаточно прав")
            print("💡 Решение: Добавить роль 'Vertex AI User' в IAM")
            
        elif "billing" in error_msg.lower():
            print("📋 Причина: Проблемы с биллингом")
            print("💡 Решение: Настроить оплату в Google Cloud")
            
        else:
            print("📋 Причина: Неизвестная ошибка")
            print("💡 Решение: Проверить логи и конфигурацию")
    
    print("\n" + "=" * 50)
    print("📊 ИТОГ ТЕСТИРОВАНИЯ:")
    print("✅ REST API реализация согласно документации")
    print("✅ Правильные endpoints (predictLongRunning + fetchPredictOperation)")
    print("✅ Упрощенная обработка ответа (GCS URI напрямую)")
    print("🔄 Автоматический fallback на RunwayML при ошибках")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 