import asyncio
from db.avatar_repository import engine, User, PendingRegistration
from sqlalchemy import select

async def check_db():
    async with engine.begin() as conn:
        # Check users
        result = await conn.execute(select(User))
        users = result.fetchall()
        print(f'Users: {len(users)}')
        for user in users:
            print(f'  - {user.username} ({user.email}) - verified: {user.is_verified}')
        
        # Check pending registrations
        result = await conn.execute(select(PendingRegistration))
        pending = result.fetchall()
        print(f'Pending registrations: {len(pending)}')
        for pending_reg in pending:
            print(f'  - {pending_reg.username} ({pending_reg.email})')

if __name__ == "__main__":
    asyncio.run(check_db()) 