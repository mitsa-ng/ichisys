import asyncio

from sqlalchemy import select

from app.config import settings
from app.database import async_session, init_db
from app.models.admin import Admin
from app.services.auth import hash_password


async def seed():
    await init_db()
    async with async_session() as db:
        result = await db.execute(select(Admin).where(Admin.email == settings.admin_email))
        if result.scalar_one_or_none():
            print("Admin already exists, skipping")
        else:
            admin = Admin(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                display_name="Admin",
            )
            db.add(admin)
            await db.commit()
            print(f"Admin user created: {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(seed())
