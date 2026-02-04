"""
Database initialization script.
Creates all tables and default admin.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from database import init_db, close_db
from database.models import Admin, AdminRole
from database import async_session_maker
from api.services.admin_service import admin_service
from config import settings


async def main():
    print("Initializing database...")
    
    # Create tables
    await init_db()
    print("Tables created successfully!")
    
    # Create default admin
    admin = await admin_service.create_default_admin()
    
    if admin:
        print(f"Default admin created: {admin.username}")
    else:
        print("Default admin already exists")
    
    await close_db()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
