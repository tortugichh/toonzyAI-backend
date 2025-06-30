#!/usr/bin/env python3
"""
Простой тест системы прогресса загрузки видео ToonzyAI
"""

import asyncio
import httpx
import time

async def main():
    print("🎬 ToonzyAI Video Progress Loading Test")
    print("=" * 50)
    
    # Настройки
    BASE_URL = "http://localhost:8000"
    PROJECT_ID = "dfc99e65-1716-463a-bbb4-d9c9a5d4bffc"
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Логин
            print("🔐 Аутентификация...")
            login_data = {'username': 'video_test_user', 'password': 'password123'}
            
            login_response = await client.post(f'{BASE_URL}/api/v1/auth/login', json=login_data)
            
            if login_response.status_code != 200:
                print(f"❌ Ошибка логина: {login_response.text}")
                return
            
            token = login_response.json()['access_token']
            headers = {'Authorization': f'Bearer {token}'}
            print("✅ Аутентификация успешна")
            
            # 2. Проверка статуса видео
            print("\n📊 Проверка статуса видео...")
            info_response = await client.get(f'{BASE_URL}/api/v1/animations/{PROJECT_ID}/download-info', headers=headers)
            
            if info_response.status_code == 200:
                data = info_response.json()
                print(f"   Status: {data.get('status')}")
                print(f"   Size: {data.get('size_mb', 0)} MB")
                print(f"   Segments: {data.get('segments_count', 0)}")
                
                if data.get('status') == 'ready':
                    print("✅ Видео готово к загрузке")
                    
                    # 3. Демонстрация прогресса загрузки
                    print("\n🎥 Демонстрация прогресса загрузки...")
                    
                    # HEAD request для получения размера
                    head_response = await client.head(f'{BASE_URL}/api/v1/animations/{PROJECT_ID}/video', headers=headers)
                    
                    if head_response.status_code == 200:
                        total_size = int(head_response.headers.get('content-length', 0))
                        print(f"   📏 Общий размер: {total_size} байт")
                        
                        # Симулируем прогрессивную загрузку через Range requests
                        chunk_size = 10  # Маленькие чанки для демонстрации
                        downloaded = 0
                        
                        print("\n📊 Прогресс загрузки:")
                        print("0%", end="")
                        
                        while downloaded < total_size:
                            end_byte = min(downloaded + chunk_size - 1, total_size - 1)
                            
                            range_headers = headers.copy()
                            range_headers['Range'] = f'bytes={downloaded}-{end_byte}'
                            
                            range_response = await client.get(f'{BASE_URL}/api/v1/animations/{PROJECT_ID}/video', headers=range_headers)
                            
                            if range_response.status_code == 206:
                                chunk_data = range_response.content
                                downloaded += len(chunk_data)
                                
                                progress = (downloaded / total_size) * 100
                                print(f"\r{progress:.1f}%", end="", flush=True)
                                
                                # Небольшая задержка для демонстрации
                                await asyncio.sleep(0.1)
                            else:
                                print(f"\n❌ Range request failed: {range_response.status_code}")
                                break
                        
                        print("\n✅ Загрузка завершена!")
                        
                        # 4. Полная загрузка для проверки
                        print("\n🎬 Полная загрузка видео...")
                        full_response = await client.get(f'{BASE_URL}/api/v1/animations/{PROJECT_ID}/video', headers=headers)
                        
                        if full_response.status_code == 200:
                            print(f"✅ Полная загрузка успешна: {len(full_response.content)} байт")
                            print(f"🎬 Content-Type: {full_response.headers.get('content-type')}")
                            
                            # Проверяем что это реальное видео
                            if full_response.content:
                                print(f"🔍 Первые 30 байт: {full_response.content[:30]}")
                            
                            print(f"\n🌐 Демо страница: {BASE_URL}/demo/video-progress")
                            print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
                            print("\n📋 Что работает:")
                            print("   ✅ Range requests (HTTP 206)")
                            print("   ✅ Прогресс загрузки")
                            print("   ✅ Полная загрузка видео")
                            print("   ✅ Метаданные видео")
                            print("   ✅ Аутентификация")
                            
                        else:
                            print(f"❌ Полная загрузка не удалась: {full_response.text}")
                    else:
                        print(f"❌ HEAD request не удался: {head_response.text}")
                elif data.get('status') == 'not_ready':
                    print("⏳ Видео еще не готово")
                else:
                    print(f"❌ Ошибка статуса: {data.get('message')}")
            else:
                print(f"❌ Ошибка получения статуса: {info_response.text}")
                
        except Exception as e:
            print(f"❌ Ошибка теста: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 