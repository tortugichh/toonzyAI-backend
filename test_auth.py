#!/usr/bin/env python3
"""
Простой тест системы аутентификации ToonzyAI
Демонстрирует как пользователи регистрируются и логинятся
"""

import requests
import json

# Настройки
BASE_URL = "http://localhost:8000"
test_user = {
    "username": "test_user_123",
    "email": "test@example.com", 
    "password": "securepassword123"
}

def test_registration():
    """Тест регистрации пользователя"""
    print("🔧 Тестируем регистрацию пользователя...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=test_user,
            timeout=10
        )
        
        if response.status_code == 201:
            user_data = response.json()
            print(f"✅ Регистрация успешна!")
            print(f"   User ID: {user_data['id']}")
            print(f"   Username: {user_data['username']}")
            print(f"   Email: {user_data['email']}")
            return True
        else:
            print(f"❌ Ошибка регистрации: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к серверу")
        print("   Убедитесь что сервер запущен: uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_login():
    """Тест логина пользователя"""
    print("\n🔑 Тестируем логин пользователя...")
    
    try:
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            tokens = response.json()
            print(f"✅ Логин успешен!")
            print(f"   Token type: {tokens['token_type']}")
            print(f"   Expires in: {tokens['expires_in']} секунд")
            print(f"   Access token: {tokens['access_token'][:50]}...")
            return tokens["access_token"]
        else:
            print(f"❌ Ошибка логина: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def test_protected_endpoint(access_token):
    """Тест защищенного эндпоинта"""
    print("\n🔒 Тестируем защищенный эндпоинт...")
    
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Доступ к защищенному эндпоинту успешен!")
            print(f"   Пользователь: {user_data['username']}")
            print(f"   Email: {user_data['email']}")
            return True
        else:
            print(f"❌ Ошибка доступа: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Главная функция теста"""
    print("🚀 Тест системы аутентификации ToonzyAI")
    print("=" * 50)
    
    # Тест регистрации
    if not test_registration():
        return
    
    # Тест логина
    access_token = test_login()
    if not access_token:
        return
    
    # Тест защищенного эндпоинта
    test_protected_endpoint(access_token)
    
    print("\n" + "=" * 50)
    print("🎉 Все тесты завершены!")
    print("\n📚 Как использовать:")
    print("1. Пользователи регистрируются через POST /api/v1/auth/register")
    print("2. Логинятся через POST /api/v1/auth/login")  
    print("3. Получают JWT токен")
    print("4. Используют токен для всех запросов к API")
    print("\n🌐 Документация API: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 