#!/usr/bin/env python3

import requests
import json
import time
import sys

def test_animation_creation():
    base_url = 'http://localhost:8000'
    
    # 1. Логин
    print("🔐 Логин...")
    login_data = {'username': 'apitest_user', 'password': 'securepassword123'}
    response = requests.post(f'{base_url}/api/v1/auth/login', json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Ошибка логина: {response.text}")
        return False
        
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print("✅ Успешный логин")
    
    # 2. Получаем аватары
    print("\n📸 Получение аватаров...")
    response = requests.get(f'{base_url}/api/v1/avatars/', headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Ошибка получения аватаров: {response.text}")
        return False
        
    avatars_data = response.json()
    avatars = avatars_data['avatars']  # Исправлено: берем поле 'avatars'
    print(f"✅ Найдено аватаров: {len(avatars)}")
    
    # 3. Создаем аватар если нужно
    if len(avatars) == 0:
        print("🎭 Создаем новый аватар...")
        avatar_data = {'prompt': 'Beautiful anime character with blue hair and friendly smile'}
        response = requests.post(f'{base_url}/api/v1/avatars/', json=avatar_data, headers=headers)
        
        if response.status_code not in [200, 201]:  # Исправлено: принимаем и 200, и 201
            print(f"❌ Ошибка создания аватара: {response.text}")
            return False
            
        avatar = response.json()
        print(f"✅ Аватар создан: {avatar['avatar_id']}")
        print("⏳ Ждем 30 секунд для завершения генерации...")
        time.sleep(30)
    else:
        avatar = avatars[0]
        print(f"🎭 Используем существующий аватар: {avatar['avatar_id']}")
    
    avatar_id = avatar['avatar_id']
    
    # 4. Создаем анимационный проект
    print("\n🎬 Создание анимационного проекта...")
    animation_data = {
        'source_avatar_id': avatar_id,
        'animation_prompt': 'A cheerful character greeting and dancing',
        'total_segments': 2,
    }
    
    response = requests.post(f'{base_url}/api/v1/animations/', json=animation_data, headers=headers)
    
    if response.status_code not in [200, 201, 202]:  # Исправлено: добавлен 202
        print(f"❌ Ошибка создания проекта: {response.status_code}")
        print(f"Детали: {response.text}")
        return False
    
    project = response.json()
    project_id = project['id']
    print(f"✅ Проект создан: {project_id}")
    print(f"📊 Статус: {project['status']}")
    print(f"🎞️ Сегментов: {len(project['segments'])}")
    
    # 5. Мониторинг статуса
    print(f"\n⏳ Мониторинг статуса проекта...")
    for i in range(30):  # Проверяем 30 раз с интервалом 10 секунд
        time.sleep(10)
        
        response = requests.get(f'{base_url}/api/v1/animations/{project_id}', headers=headers)
        if response.status_code != 200:
            print(f"❌ Ошибка получения статуса: {response.text}")
            continue
            
        updated_project = response.json()
        status = updated_project['status']
        segments = updated_project['segments']
        
        print(f"\n🔄 Проверка {i+1}/30:")
        print(f"📊 Статус проекта: {status}")
        
        for j, segment in enumerate(segments):
            print(f"   🎬 Сегмент {j+1}: {segment['status']}")
            if segment.get('video_url'):
                print(f"      📹 Видео: {segment['video_url']}")
        
        if updated_project.get('final_video_url'):
            print(f"🎉 Финальное видео: {updated_project['final_video_url']}")
            
        if status in ['completed', 'failed']:
            print(f"\n{'✅' if status == 'completed' else '❌'} Проект завершен со статусом: {status}")
            break
    else:
        print("\n⏰ Превышено время ожидания (5 минут)")
    
    return True

if __name__ == "__main__":
    print("🚀 Тестирование создания анимации...")
    success = test_animation_creation()
    sys.exit(0 if success else 1) 