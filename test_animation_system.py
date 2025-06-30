#!/usr/bin/env python3
"""
Тест системы анимации ToonzyAI
Проверяет JWT аутентификацию и API анимации
"""

import requests
import json
import time
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def test_animation_system():
    """
    Полный тест системы анимации
    """
    print("🚀 Тестируем систему анимации ToonzyAI")
    print("=" * 50)
    
    # 1. Регистрация пользователя
    print("1️⃣ Регистрация нового пользователя...")
    username = f"testuser_{str(uuid4())[:8]}"
    user_data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=user_data)
    if response.status_code in [200, 201]:
        print(f"✅ Пользователь {username} зарегистрирован")
    else:
        print(f"❌ Ошибка регистрации: {response.text}")
        return
    
    # 2. Вход в систему
    print("2️⃣ Авторизация...")
    login_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens["access_token"]
        print("✅ Авторизация успешна")
    else:
        print(f"❌ Ошибка авторизации: {response.text}")
        return
    
    # Headers для аутентифицированных запросов
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 3. Создание аватара (для начала анимации)
    print("3️⃣ Создание аватара...")
    avatar_data = {
        "prompt": "Beautiful cartoon character, anime style, smiling"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/avatars/", json=avatar_data, headers=headers)
    if response.status_code == 201:
        avatar = response.json()
        avatar_id = avatar["id"]
        print(f"✅ Аватар создан: {avatar_id}")
    else:
        print(f"❌ Ошибка создания аватара: {response.text}")
        return
    
    # 4. Создание проекта анимации
    print("4️⃣ Создание проекта анимации...")
    animation_data = {
        "source_avatar_id": avatar_id,
        "total_segments": 3,
        "animation_prompt": "Character walking happily in a magical forest"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/animations/", json=animation_data, headers=headers)
    if response.status_code == 202:
        project = response.json()
        project_id = project["id"]
        print(f"✅ Проект анимации создан: {project_id}")
        print(f"   Статус: {project['status']}")
        print(f"   Сегментов: {project['total_segments']}")
    else:
        print(f"❌ Ошибка создания проекта: {response.text}")
        return
    
    # 5. Проверка статуса проекта
    print("5️⃣ Проверка статуса проекта...")
    
    for i in range(3):  # Проверяем 3 раза с паузой
        response = requests.get(f"{BASE_URL}/api/v1/animations/{project_id}", headers=headers)
        if response.status_code == 200:
            project_status = response.json()
            print(f"   Итерация {i+1}: Статус - {project_status['status']}")
            print(f"   Сегментов обработано: {len([s for s in project_status['segments'] if s['status'] == 'completed'])}/{project_status['total_segments']}")
            
            # Показываем статус каждого сегмента
            for segment in project_status['segments']:
                print(f"     Сегмент {segment['segment_number']}: {segment['status']}")
        else:
            print(f"❌ Ошибка получения статуса: {response.text}")
        
        if i < 2:  # Не спим на последней итерации
            time.sleep(2)
    
    # 6. Тест принудительной сборки видео (если сегменты готовы)
    print("6️⃣ Попытка запуска сборки видео...")
    response = requests.post(f"{BASE_URL}/api/v1/animations/{project_id}/assemble", headers=headers)
    if response.status_code == 200:
        assembly_result = response.json()
        print(f"✅ Сборка запущена: {assembly_result['message']}")
    else:
        print(f"ℹ️ Сборка не запущена: {response.text}")
    
    # 7. Получение списка всех проектов
    print("7️⃣ Получение списка проектов...")
    response = requests.get(f"{BASE_URL}/api/v1/animations/", headers=headers)
    if response.status_code == 200:
        projects = response.json()
        print(f"✅ Найдено проектов: {len(projects)}")
        for proj in projects:
            print(f"   - {proj['id']}: {proj['status']} ({proj['total_segments']} сегментов)")
    else:
        print(f"❌ Ошибка получения списка: {response.text}")
    
    print("=" * 50)
    print("🎬 Тест системы анимации завершен!")
    print(f"🔗 Документация API: {BASE_URL}/docs")
    print("📝 Примечание: Для полного функционирования нужны:")
    print("   - Celery worker (celery -A celery_worker worker --loglevel=info)")
    print("   - Redis server")
    print("   - Настройки Google Cloud (Vertex AI + GCS)")


if __name__ == "__main__":
    try:
        test_animation_system()
    except Exception as e:
        print(f"❌ Критическая ошибка теста: {e}")
        print("🔍 Проверьте, что сервер запущен на http://localhost:8000") 