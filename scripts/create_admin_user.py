import asyncio
import os
from db.avatar_repository import async_session, User
from utils.auth import get_password_hash
from sqlalchemy import select

async def create_admin_user():
    username = "tortugich_admin"
    email = "tortugich_admin@localhost.com"  # valid email
    password = "admin_user96"
    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        hashed_password = get_password_hash(password)
        if user:
            user.email = email
            user.hashed_password = hashed_password
            user.is_active = True
            user.is_verified = True
            user.is_admin = True
            await session.commit()
            print(f"Admin user '{username}' updated successfully.")
            return
        admin_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=True,
            is_admin=True,
        )
        session.add(admin_user)
        await session.commit()
        print(f"Admin user '{username}' created successfully.")

if __name__ == "__main__":
    asyncio.run(create_admin_user()) 