import asyncio
import httpx
import json

async def test_registration():
    # Test data
    test_user = {
        "username": "testuser123",
        "email": "test123@example.com",
        "password": "TestPassword123"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Test registration
            response = await client.post(
                "http://localhost:8000/api/v1/auth/register",
                json=test_user,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Registration response status: {response.status_code}")
            print(f"Registration response body: {response.text}")
            
            # Test login with the same credentials
            login_data = {
                "login": test_user["username"],
                "password": test_user["password"]
            }
            
            response = await client.post(
                "http://localhost:8000/api/v1/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Login response status: {response.status_code}")
            print(f"Login response body: {response.text}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_registration()) 