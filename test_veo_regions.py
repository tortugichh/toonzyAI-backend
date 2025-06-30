#!/usr/bin/env python3
"""
Тест доступности Veo в разных регионах
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.vertex_ai_client_v2 import test_veo_availability_in_regions

async def main():
    print("🔍 Тестирование доступности Veo в разных регионах...")
    print("=" * 60)
    
    results = await test_veo_availability_in_regions()
    
    print("\n📊 РЕЗУЛЬТАТЫ:")
    print("=" * 60)
    
    available_regions = []
    
    for region, info in results.items():
        status = info.get("status", "Unknown")
        
        if status == "✅ Available":
            model = info.get("model", "unknown")
            print(f"✅ {region:<18} | {model}")
            available_regions.append(region)
        else:
            error = info.get("error", "Unknown error")
            print(f"❌ {region:<18} | {error}")
    
    print("=" * 60)
    
    if available_regions:
        print(f"\n🎉 НАЙДЕНЫ ДОСТУПНЫЕ РЕГИОНЫ: {len(available_regions)}")
        print("\n💡 Чтобы использовать лучший регион, добавьте в .env:")
        best_region = available_regions[0]
        print(f"VERTEX_LOCATION={best_region}")
        
        print(f"\n🚀 Или экспортируйте переменную:")
        print(f"export VERTEX_LOCATION={best_region}")
        
    else:
        print("\n😔 НИ ОДИН РЕГИОН НЕ ДОСТУПЕН")
        print("💡 Возможные причины:")
        print("   - Проект не имеет доступа к Veo")
        print("   - Нужно запросить доступ к Veo Waitlist")
        print("   - Проблемы с аутентификацией")
        
        print("\n🔧 Рекомендация: Используйте RunwayML как альтернативу")

if __name__ == "__main__":
    asyncio.run(main()) 