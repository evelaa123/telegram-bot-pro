"""
Authentication router.
Handles login, logout, token refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.schemas.auth import (
    Token, AdminLogin, AdminCreate, AdminResponse,
    RefreshTokenRequest, PasswordChange
)
from api.services.admin_service import admin_service
from api.services.auth_service import (
    auth_service, get_current_admin, require_role
)
from database.models import Admin
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with username and password.
    Returns access and refresh tokens.
    """
    admin = await admin_service.authenticate(
        form_data.username,
        form_data.password
    )
    
    if not admin:
        logger.warning("Failed login attempt", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = auth_service.create_access_token(
        data={"sub": admin.username, "role": admin.role.value}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": admin.username, "role": admin.role.value}
    )
    
    logger.info("Admin logged in", username=admin.username)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    """
    token_data = auth_service.verify_refresh_token(request.refresh_token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    admin = await admin_service.get_admin_by_username(token_data.username)
    
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found or deactivated"
        )
    
    # Create new tokens
    access_token = auth_service.create_access_token(
        data={"sub": admin.username, "role": admin.role.value}
    )
    new_refresh_token = auth_service.create_refresh_token(
        data={"sub": admin.username, "role": admin.role.value}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.get("/me", response_model=AdminResponse)
async def get_current_admin_info(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get current admin's information."""
    return AdminResponse.model_validate(current_admin)


@router.post("/change-password")
async def change_password(
    request: PasswordChange,
    current_admin: Admin = Depends(get_current_admin)
):
    """Change current admin's password."""
    # Verify current password
    if not admin_service.verify_password(
        request.current_password,
        current_admin.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    await admin_service.change_password(
        current_admin.id,
        request.new_password
    )
    
    logger.info("Password changed", admin_id=current_admin.id)
    
    return {"message": "Password changed successfully"}


# Superadmin-only routes
@router.post("/admins", response_model=AdminResponse)
async def create_admin(
    request: AdminCreate,
    current_admin: Admin = Depends(require_role(["superadmin"]))
):
    """Create new admin user. Superadmin only."""
    # Check if username exists
    existing = await admin_service.get_admin_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    admin = await admin_service.create_admin(
        username=request.username,
        password=request.password,
        role=request.role
    )
    
    return AdminResponse.model_validate(admin)


@router.get("/admins", response_model=list[AdminResponse])
async def list_admins(
    current_admin: Admin = Depends(require_role(["superadmin"]))
):
    """List all admins. Superadmin only."""
    admins = await admin_service.list_admins()
    return [AdminResponse.model_validate(a) for a in admins]


@router.delete("/admins/{admin_id}")
async def deactivate_admin(
    admin_id: int,
    current_admin: Admin = Depends(require_role(["superadmin"]))
):
    """Deactivate admin account. Superadmin only."""
    if admin_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    success = await admin_service.deactivate_admin(admin_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return {"message": "Admin deactivated"}
