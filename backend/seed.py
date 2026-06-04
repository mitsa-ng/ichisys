import asyncio

from sqlalchemy import select

from app.database import async_session, init_db
from app.models.admin import Admin
from app.services.auth import hash_password


async def seed():
    await init_db()
    async with async_session() as db:
        result = await db.execute(select(Admin).where(Admin.email == "admin@ichiban.com"))
        if result.scalar_one_or_none():
            print("Admin already exists, skipping")
        else:
            admin = Admin(
                email="admin@ichiban.com",
                hashed_password=hash_password("admin123"),
                display_name="Admin",
            )
            db.add(admin)
            await db.commit()
            print("Admin user created: admin@ichiban.com / admin123")


if __name__ == "__main__":
    asyncio.run(seed())
