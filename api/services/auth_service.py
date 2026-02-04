"""
JWT authentication service.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from api.schemas.auth import TokenData
from api.services.admin_service import admin_service
from database.models import Admin
from config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = "HS256"


class AuthService:
    """JWT authentication service."""
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.admin_access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(
            to_encode,
            settings.admin_secret_key,
            algorithm=ALGORITHM
        )
    
    def create_refresh_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=settings.admin_refresh_token_expire_days
            )
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(
            to_encode,
            settings.admin_secret_key,
            algorithm=ALGORITHM
        )
    
    def decode_token(self, token: str) -> Optional[TokenData]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.admin_secret_key,
                algorithms=[ALGORITHM]
            )
            
            username: str = payload.get("sub")
            role: str = payload.get("role")
            token_type: str = payload.get("type")
            
            if username is None:
                return None
            
            return TokenData(username=username, role=role)
            
        except JWTError:
            return None
    
    def verify_refresh_token(self, token: str) -> Optional[TokenData]:
        """Verify refresh token and return token data."""
        try:
            payload = jwt.decode(
                token,
                settings.admin_secret_key,
                algorithms=[ALGORITHM]
            )
            
            if payload.get("type") != "refresh":
                return None
            
            username: str = payload.get("sub")
            role: str = payload.get("role")
            
            if username is None:
                return None
            
            return TokenData(username=username, role=role)
            
        except JWTError:
            return None


# Global service instance
auth_service = AuthService()


# Dependency functions
async def get_current_admin(
    token: str = Depends(oauth2_scheme)
) -> Admin:
    """
    Dependency to get current authenticated admin.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = auth_service.decode_token(token)
    
    if token_data is None:
        raise credentials_exception
    
    admin = await admin_service.get_admin_by_username(token_data.username)
    
    if admin is None:
        raise credentials_exception
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is deactivated"
        )
    
    return admin


async def get_current_active_admin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """Dependency to get current active admin."""
    return current_admin


def require_role(allowed_roles: list):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin-only")
        async def admin_route(admin: Admin = Depends(require_role(["superadmin", "admin"]))):
            ...
    """
    async def role_checker(
        current_admin: Admin = Depends(get_current_admin)
    ) -> Admin:
        if current_admin.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_admin
    
    return role_checker
