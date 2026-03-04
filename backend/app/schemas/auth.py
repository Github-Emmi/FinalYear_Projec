"""
Authentication & Authorization Schemas
User login, registration, token responses, password reset
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal
import re


class UserLogin(BaseModel):
    """Email/password login request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    remember_me: bool = Field(False, description="Keep user logged in for 30 days")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "student@school.edu",
            "password": "SecurePass123!",
            "remember_me": True
        }
    })


class UserRegister(BaseModel):
    """Student self-registration schema"""
    email: EmailStr = Field(..., description="Unique email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=12, description="Strong password required")
    password_confirm: str = Field(..., description="Password confirmation")
    first_name: str = Field(..., min_length=2, max_length=150, description="First name")
    last_name: str = Field(..., min_length=2, max_length=150, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Enforce password complexity: 1 uppercase, 1 lowercase, 1 digit, 1 special char"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        """Ensure password and confirmation match"""
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Username must be alphanumeric + underscore"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "newstudent@school.edu",
            "username": "new_student_123",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890"
        }
    })


class TokenResponse(BaseModel):
    """JWT token pair response"""
    access_token: str = Field(..., description="Access token (15-min expiry)")
    refresh_token: str = Field(..., description="Refresh token (7-day expiry)")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until access token expires")
    user: 'UserResponse' = Field(..., description="Authenticated user data")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 900,
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "john_doe",
                "email": "john@school.edu",
                "first_name": "John",
                "last_name": "Doe",
                "user_type": "STUDENT",
                "is_active": True
            }
        }
    })


class RefreshTokenRequest(BaseModel):
    """Refresh JWT access token"""
    refresh_token: str = Field(..., description="Valid refresh token")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    })


class UserResponse(BaseModel):
    """User profile response"""
    id: UUID = Field(..., description="User unique identifier")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email address")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    user_type: Literal["ADMIN", "STAFF", "STUDENT"] = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "john_doe",
                "email": "john@school.edu",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1234567890",
                "user_type": "STUDENT",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-03-03T15:45:00Z"
            }
        }
    )


class PasswordResetRequest(BaseModel):
    """Request password reset token"""
    email: EmailStr = Field(..., description="Email address for reset")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "john@school.edu"
        }
    })


class PasswordResetConfirm(BaseModel):
    """Reset password with token"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=12, description="New password")
    new_password_confirm: str = Field(..., description="Confirm new password")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Enforce password complexity"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('new_password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        """Ensure passwords match"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "abc123defg456hij789",
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!"
        }
    })


class ChangePasswordRequest(BaseModel):
    """Change password for authenticated user"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=12, description="New password")
    new_password_confirm: str = Field(..., description="Confirm new password")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Enforce password complexity"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('new_password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        """Ensure passwords match"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


# Update forward reference
TokenResponse.model_rebuild()
