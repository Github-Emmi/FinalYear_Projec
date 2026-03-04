"""
User Authentication & Registration Validation Schemas
Focused on Login, Registration, Token Management, and Password Operations
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal
import re


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    remember_me: bool = Field(False, description="Keep user logged in longer")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Ensure password meets minimum requirements"""
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        if not any(c.isdigit() for c in v):
            raise ValueError('password must contain at least one number')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "john@school.com",
            "password": "secure123",
            "remember_me": False
        }
    })


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=20, description="Username (3-20 chars, alphanumeric + underscore)")
    password: str = Field(..., min_length=8, description="Strong password (8+ chars)")
    confirm_password: str = Field(..., description="Confirm password - must match password")
    
    first_name: str = Field(..., min_length=2, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=2, max_length=100, description="User's last name")
    
    role: Literal["student", "staff", "admin"] = Field(..., description="User role")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number (optional)")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Username must be alphanumeric + underscore, no spaces"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('username can only contain letters, numbers, and underscores (no spaces)')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """
        Password must contain:
        - At least 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number
        - At least 1 special character
        """
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('password must contain at least one special character (!@#$%^&*...)')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """Confirm password must match password"""
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('confirm_password must match password')
        return v
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v):
        """Names must only contain letters and spaces"""
        if not re.match(r'^[a-zA-Z\s\-\']+$', v):
            raise ValueError('name can only contain letters, spaces, hyphens, and apostrophes')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "john@school.com",
            "username": "john_doe",
            "password": "Secure@123Pass",
            "confirm_password": "Secure@123Pass",
            "first_name": "John",
            "last_name": "Doe",
            "role": "student",
            "phone": "+1234567890"
        }
    })


class TokenResponse(BaseModel):
    """JWT Token response"""
    access_token: str = Field(..., description="JWT access token (valid for 15 minutes)")
    refresh_token: str = Field(..., description="JWT refresh token (valid for 7 days)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=900, description="Access token expiry in seconds (900 = 15 mins)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 900
        }
    })


class UserResponse(BaseModel):
    """User profile response"""
    id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    
    role: Literal["student", "staff", "admin"] = Field(..., description="User role")
    is_active: bool = Field(default=True, description="Account active status")
    is_verified: bool = Field(default=False, description="Email verified status")
    
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "john@school.com",
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "role": "student",
            "is_active": True,
            "is_verified": True,
            "created_at": "2024-03-01T10:00:00",
            "last_login": "2024-03-15T09:30:00"
        }
    })


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str = Field(..., min_length=8, description="Current password for verification")
    new_password: str = Field(..., min_length=8, description="New password (must meet strength requirements)")
    confirm_password: str = Field(..., description="Confirm new password - must match new_password")
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password_strength(cls, v):
        """New password must meet strength requirements"""
        if len(v) < 8:
            raise ValueError('new password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('new password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('new password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('new password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('new password must contain at least one special character')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """Confirm password must match new password"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('confirm_password must match new_password')
        return v
    
    @field_validator('current_password')
    @classmethod
    def validate_different_password(cls, v, info):
        """New password must be different from current password"""
        if 'new_password' in info.data and v == info.data['new_password']:
            raise ValueError('new password must be different from current password')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "current_password": "OldPass@123",
            "new_password": "NewSecure@456",
            "confirm_password": "NewSecure@456"
        }
    })


class ForgotPasswordRequest(BaseModel):
    """Password reset request"""
    email: EmailStr = Field(..., description="Email address associated with account")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "john@school.com"
        }
    })


class ForgotPasswordConfirm(BaseModel):
    """Password reset confirmation with token"""
    token: str = Field(..., description="Password reset token (sent to email)")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password_strength(cls, v):
        """New password must meet strength requirements"""
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('password must contain at least one special character')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """Confirm password must match new password"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('confirm_password must match new_password')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "new_password": "NewSecure@456",
            "confirm_password": "NewSecure@456"
        }
    })


class UserProfileUpdateRequest(BaseModel):
    """Update user profile"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v):
        """Names must only contain letters and spaces"""
        if v and not re.match(r'^[a-zA-Z\s\-\']+$', v):
            raise ValueError('name can only contain letters, spaces, hyphens, and apostrophes')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "first_name": "John",
            "last_name": "Smith",
            "phone": "+1234567890"
        }
    })
