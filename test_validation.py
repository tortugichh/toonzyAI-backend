#!/usr/bin/env python3
"""
Тест валидации ToonzyAI Authentication System
Демонстрирует все уровни валидации
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_pydantic_validation():
    """Тест Pydantic валидации на уровне схем"""
    print("\n🔍 Тестируем Pydantic валидацию...")
    
    # Тест короткого username
    print("📝 Тест: Слишком короткий username (меньше 3 символов)")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": "ab",  # Слишком короткий
        "email": "test@example.com",
        "password": "password123"
    })
    if response.status_code == 422:
        error = response.json()
        print(f"✅ Валидация сработала: {error['detail'][0]['msg']}")
    
    # Тест недопустимых символов в username
    print("📝 Тест: Недопустимые символы в username")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": "test-user@",  # Недопустимые символы
        "email": "test@example.com", 
        "password": "password123"
    })
    if response.status_code == 422:
        print("✅ Валидация недопустимых символов сработала")
    
    # Тест неправильного email
    print("📝 Тест: Неправильный формат email")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": "testuser",
        "email": "not-an-email",  # Неправильный email
        "password": "password123"
    })
    if response.status_code == 422:
        print("✅ Валидация email сработала")
    
    # Тест короткого пароля
    print("📝 Тест: Слишком короткий пароль (меньше 8 символов)")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "123"  # Слишком короткий
    })
    if response.status_code == 422:
        print("✅ Валидация пароля сработала")

def test_business_logic_validation():
    """Тест бизнес-логики валидации"""
    print("\n🔍 Тестируем бизнес-логику валидацию...")
    
    # Создаем пользователя
    test_user = {
        "username": "duplicate_test",
        "email": "duplicate@example.com",
        "password": "password123"
    }
    
    print("📝 Создаем первого пользователя...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=test_user)
    if response.status_code == 201:
        print("✅ Первый пользователь создан")
        
        # Пытаемся создать с тем же username
        print("📝 Тест: Дублирование username")
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "username": "duplicate_test",  # Дубликат
            "email": "different@example.com",
            "password": "password123"
        })
        if response.status_code == 400:
            error = response.json()
            print(f"✅ Валидация дубликата username: {error['detail']}")
        
        # Пытаемся создать с тем же email
        print("📝 Тест: Дублирование email")
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "username": "different_user",
            "email": "duplicate@example.com",  # Дубликат
            "password": "password123"
        })
        if response.status_code == 400:
            error = response.json()
            print(f"✅ Валидация дубликата email: {error['detail']}")

def test_authentication_validation():
    """Тест валидации аутентификации"""
    print("\n🔍 Тестируем валидацию аутентификации...")
    
    # Тест неправильного пароля
    print("📝 Тест: Неправильный пароль")
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "duplicate_test",
        "password": "wrongpassword"  # Неправильный пароль
    })
    if response.status_code == 401:
        error = response.json()
        print(f"✅ Валидация неправильного пароля: {error['detail']}")
    
    # Тест несуществующего пользователя
    print("📝 Тест: Несуществующий пользователь")
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "nonexistent_user",
        "password": "password123"
    })
    if response.status_code == 401:
        print("✅ Валидация несуществующего пользователя сработала")

def test_token_validation():
    """Тест валидации токенов"""
    print("\n🔍 Тестируем валидацию токенов...")
    
    # Тест без токена
    print("📝 Тест: Доступ без токена")
    response = requests.get(f"{BASE_URL}/api/v1/auth/me")
    if response.status_code == 401:
        print("✅ Доступ без токена заблокирован")
    
    # Тест с недействительным токеном
    print("📝 Тест: Недействительный токен")
    headers = {"Authorization": "Bearer invalid_token_here"}
    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    if response.status_code == 401:
        print("✅ Недействительный токен отклонен")
    
    # Тест с неправильным форматом токена
    print("📝 Тест: Неправильный формат токена")
    headers = {"Authorization": "InvalidFormat token"}
    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    if response.status_code in [401, 403]:
        print("✅ Неправильный формат токена отклонен")

def main():
    """Главная функция тестирования валидации"""
    print("🔍 Тестирование системы валидации ToonzyAI")
    print("=" * 60)
    
    try:
        test_pydantic_validation()
        test_business_logic_validation()
        test_authentication_validation()
        test_token_validation()
        
        print("\n" + "=" * 60)
        print("🎉 Все тесты валидации завершены!")
        print("\n📋 Система включает:")
        print("✅ Pydantic валидацию (формат данных)")
        print("✅ Валидацию базы данных (уникальность)")
        print("✅ Бизнес-логику валидацию")
        print("✅ Валидацию аутентификации")
        print("✅ Валидацию JWT токенов")
        
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к серверу")
        print("   Запустите сервер: uvicorn main:app --reload")

if __name__ == "__main__":
    main() 