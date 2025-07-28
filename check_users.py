import asyncio
import os
import sys
sys.path.append('.')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:turtle96@localhost:5433/toonzy-ai")

async def check_users():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Check users table
        result = await conn.execute(select("*").select_from("users"))
        users = result.fetchall()
        print(f"Users in database: {len(users)}")
        for user in users:
            print(f"  - ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Verified: {user[4]}, Active: {user[3]}")
        
        # Check pending registrations
        result = await conn.execute(select("*").select_from("pending_registrations"))
        pending = result.fetchall()
        print(f"Pending registrations: {len(pending)}")
        for pending_reg in pending:
            print(f"  - ID: {pending_reg[0]}, Username: {pending_reg[1]}, Email: {pending_reg[2]}")

if __name__ == "__main__":
    asyncio.run(check_users()) 