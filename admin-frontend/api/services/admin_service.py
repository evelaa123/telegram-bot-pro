"""
Admin service for managing admin users.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from passlib.context import CryptContext

from database import async_session_maker
from database.models import Admin, AdminRole
from config import settings
import structlog

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminService:
    """Service for managing admin users."""
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash password."""
        return pwd_context.hash(password)
    
    async def create_default_admin(self) -> Optional[Admin]:
        """Create default admin user if none exists."""
        async with async_session_maker() as session:
            # Check if any admin exists
            result = await session.execute(select(Admin).limit(1))
            existing = result.scalar_one_or_none()
            
            if existing:
                return None
            
            # Create default admin
            admin = Admin(
                username=settings.default_admin_username,
                password_hash=self.hash_password(settings.default_admin_password),
                role=AdminRole.SUPERADMIN,
                is_active=True
            )
            
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            
            logger.info(
                "Default admin created",
                username=settings.default_admin_username
            )
            
            return admin
    
    async def authenticate(
        self,
        username: str,
        password: str
    ) -> Optional[Admin]:
        """
        Authenticate admin by username and password.
        
        Returns:
            Admin if authenticated, None otherwise
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(Admin).where(
                    Admin.username == username,
                    Admin.is_active == True
                )
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                return None
            
            if not self.verify_password(password, admin.password_hash):
                return None
            
            # Update last login
            await session.execute(
                update(Admin)
                .where(Admin.id == admin.id)
                .values(last_login_at=datetime.utcnow())
            )
            await session.commit()
            
            return admin
    
    async def get_admin_by_username(self, username: str) -> Optional[Admin]:
        """Get admin by username."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Admin).where(Admin.username == username)
            )
            return result.scalar_one_or_none()
    
    async def get_admin_by_id(self, admin_id: int) -> Optional[Admin]:
        """Get admin by ID."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Admin).where(Admin.id == admin_id)
            )
            return result.scalar_one_or_none()
    
    async def create_admin(
        self,
        username: str,
        password: str,
        role: str = "viewer"
    ) -> Admin:
        """Create new admin user."""
        async with async_session_maker() as session:
            admin = Admin(
                username=username,
                password_hash=self.hash_password(password),
                role=AdminRole(role),
                is_active=True
            )
            
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            
            logger.info("Admin created", username=username, role=role)
            
            return admin
    
    async def list_admins(self) -> List[Admin]:
        """List all admins."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Admin).order_by(Admin.created_at.desc())
            )
            return list(result.scalars().all())
    
    async def update_admin_role(
        self,
        admin_id: int,
        new_role: str
    ) -> Optional[Admin]:
        """Update admin role."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Admin).where(Admin.id == admin_id)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                return None
            
            admin.role = AdminRole(new_role)
            await session.commit()
            await session.refresh(admin)
            
            logger.info(
                "Admin role updated",
                admin_id=admin_id,
                new_role=new_role
            )
            
            return admin
    
    async def deactivate_admin(self, admin_id: int) -> bool:
        """Deactivate admin account."""
        async with async_session_maker() as session:
            result = await session.execute(
                update(Admin)
                .where(Admin.id == admin_id)
                .values(is_active=False)
            )
            await session.commit()
            
            if result.rowcount > 0:
                logger.info("Admin deactivated", admin_id=admin_id)
                return True
            return False
    
    async def change_password(
        self,
        admin_id: int,
        new_password: str
    ) -> bool:
        """Change admin password."""
        async with async_session_maker() as session:
            result = await session.execute(
                update(Admin)
                .where(Admin.id == admin_id)
                .values(password_hash=self.hash_password(new_password))
            )
            await session.commit()
            
            return result.rowcount > 0


# Global service instance
admin_service = AdminService()
