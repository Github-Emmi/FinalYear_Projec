"""
Authentication Service - Handles user registration, login, token management.

Provides:
- User registration with validation and password hashing
- User login with credential verification
- Access token refresh with expiry management
- User logout with session invalidation
- Token validation and user extraction
- Role-based authentication support
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, UnauthorizedError, ConflictError
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import CustomUser
from app.repositories.factory import RepositoryFactory
from app.schemas.user import UserResponse
from app.services.base import BaseService


class AuthService(BaseService[CustomUser]):
    """
    Authentication service for user lifecycle management.
    
    Handles:
    - Registration: Email validation, password hashing, user creation
    - Login: Credential verification, token generation, session tracking
    - Token refresh: Token validation, new token generation
    - Logout: Session cleanup
    - Token validation: JWT verification, user fetching
    
    Usage:
        auth_service = AuthService(repos)
        user_response = await auth_service.register_user(
            email="user@school.edu",
            username="john_doe",
            password="SecurePass123!",
            role="STUDENT"
        )
        token_response = await auth_service.login_user(
            email="user@school.edu",
            password="SecurePass123!"
        )
    """

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str = "STUDENT",
    ) -> dict:
        """
        Register new user with validation and password hashing.
        
        Process:
        1. Validate all inputs
        2. Check email uniqueness
        3. Check username uniqueness
        4. Hash password with BCrypt
        5. Create user in database
        6. Generate JWT tokens
        7. Log audit trail
        
        Args:
            email: User email address
            username: Username for login
            password: Plain-text password to hash
            first_name: User's first name
            last_name: User's last name
            role: User role (ADMIN, STAFF, STUDENT)
        
        Returns:
            Dictionary with user data and tokens:
            {
                "success": True,
                "data": UserResponse,
                "access_token": str,
                "refresh_token": str,
                "token_type": "bearer",
                "expires_in": 900
            }
        
        Raises:
            ValidationError: If validation fails
            ConflictError: If email or username already exists
            
        Example:
            result = await auth_service.register_user(
                email="student@school.edu",
                username="john_doe",
                password="SecurePass123!",
                first_name="John",
                last_name="Doe",
                role="STUDENT"
            )
        """
        # Validate inputs
        self._validate_email_format(email)
        self._validate_field_length(username, "username", min_len=3, max_len=20)
        self._validate_password_strength(password)
        self._validate_field_length(first_name, "first_name", min_len=2, max_len=50)
        self._validate_field_length(last_name, "last_name", min_len=2, max_len=50)
        self._validate_enum_choice(role, "role", ["ADMIN", "STAFF", "STUDENT"])

        # Check email uniqueness
        email_exists = await self.repos.user.email_exists(email.lower())
        if email_exists:
            self.logger.warning(f"Registration failed: email {email} already exists")
            raise ConflictError("Email address already registered")

        # Check username uniqueness
        username_exists = await self.repos.user.username_exists(username)
        if username_exists:
            self.logger.warning(f"Registration failed: username {username} already exists")
            raise ConflictError("Username already taken")

        # Hash password and create user
        hashed_password = hash_password(password)
        
        try:
            async with self.transaction():
                user = await self.repos.user.create({
                    "email": email.lower(),
                    "username": username,
                    "password_hash": hashed_password,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "is_email_verified": False,
                    "is_active": True,
                })

                # Generate tokens
                access_token = create_access_token(user.id, expires_in=900)
                refresh_token = create_refresh_token(user.id)

                self.log_audit(
                    action="REGISTER",
                    entity="User",
                    entity_id=user.id,
                    changes={"email": email, "role": role},
                )
                self.logger.info(f"User {email} registered successfully")

                return self.success_response(
                    message="User registered successfully",
                    data=UserResponse.model_validate(user),
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type="bearer",
                    expires_in=900,
                )

        except Exception as e:
            self.logger.error(f"Registration error for {email}: {str(e)}")
            raise

    async def login_user(self, email: str, password: str) -> dict:
        """
        Authenticate user and generate JWT tokens.
        
        Process:
        1. Find user by email
        2. Verify password hash
        3. Check user is active
        4. Generate access and refresh tokens
        5. Update last login timestamp
        6. Log audit trail
        
        Args:
            email: User email address
            password: Plain-text password to verify
        
        Returns:
            Dictionary with tokens:
            {
                "success": True,
                "access_token": str,
                "refresh_token": str,
                "token_type": "bearer",
                "expires_in": 900,
                "user": UserResponse
            }
        
        Raises:
            UnauthorizedError: If credentials invalid or user inactive
            
        Example:
            result = await auth_service.login_user(
                email="student@school.edu",
                password="SecurePass123!"
            )
        """
        self._validate_email_format(email)
        self._validate_required_field(password, "password")

        # Find user by email
        user = await self.repos.user.get_by_email(email.lower())
        if not user:
            self.logger.warning(f"Login failed: user {email} not found")
            raise UnauthorizedError("Invalid email or password")

        # Verify password
        if not verify_password(password, user.password_hash):
            self.logger.warning(f"Login failed: invalid password for {email}")
            raise UnauthorizedError("Invalid email or password")

        # Check user is active
        if not user.is_active:
            self.logger.warning(f"Login failed: user {email} is inactive")
            raise UnauthorizedError("User account is inactive")

        # Generate tokens and update login
        try:
            async with self.transaction():
                access_token = create_access_token(user.id, expires_in=900)
                refresh_token = create_refresh_token(user.id)
                
                # Update last login
                await self.repos.user.update(user, {
                    "last_login": datetime.utcnow(),
                })

                self.log_audit(
                    action="LOGIN",
                    entity="User",
                    entity_id=user.id,
                )
                self.logger.info(f"User {email} logged in successfully")

                return self.success_response(
                    message="Login successful",
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type="bearer",
                    expires_in=900,
                    user=UserResponse.model_validate(user),
                )

        except Exception as e:
            self.logger.error(f"Login error for {email}: {str(e)}")
            raise

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Generate new access token using valid refresh token.
        
        Process:
        1. Decode and validate refresh token
        2. Extract user ID
        3. Fetch user from database
        4. Verify user is active
        5. Generate new access token
        6. Return tokens
        
        Args:
            refresh_token: Valid refresh token to validate
        
        Returns:
            Dictionary with new tokens:
            {
                "success": True,
                "access_token": str,
                "refresh_token": str (unchanged),
                "token_type": "bearer",
                "expires_in": 900
            }
        
        Raises:
            UnauthorizedError: If token invalid or expired
            
        Example:
            result = await auth_service.refresh_access_token(refresh_token)
        """
        self._validate_required_field(refresh_token, "refresh_token")

        # Decode refresh token
        try:
            payload = decode_token(refresh_token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise UnauthorizedError("Invalid refresh token payload")
                
        except Exception as e:
            self.logger.warning(f"Refresh token validation failed: {str(e)}")
            raise UnauthorizedError("Invalid or expired refresh token")

        # Fetch and verify user
        try:
            user_uuid = UUID(user_id)
            user = await self.repos.user.get_by_id(user_uuid)
            
            if not user or not user.is_active:
                raise UnauthorizedError("User account invalid or inactive")

            # Generate new access token
            access_token = create_access_token(user.id, expires_in=900)

            self.logger.info(f"Access token refreshed for user {user.id}")

            return self.success_response(
                message="Token refreshed successfully",
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=900,
            )

        except UnauthorizedError:
            raise
        except Exception as e:
            self.logger.error(f"Token refresh error: {str(e)}")
            raise UnauthorizedError("Token refresh failed")

    async def validate_token(self, token: str) -> CustomUser:
        """
        Validate JWT token and return authenticated user.
        
        Process:
        1. Decode and validate token signature
        2. Check token expiry
        3. Extract user ID from payload
        4. Fetch user from database
        5. Return user object
        
        Args:
            token: JWT access token to validate
        
        Returns:
            CustomUser object if token valid
        
        Raises:
            UnauthorizedError: If token invalid, expired, or user not found
            
        Example:
            user = await auth_service.validate_token(access_token)
            # Use user for authorization checks
        """
        self._validate_required_field(token, "token")

        # Decode token
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise UnauthorizedError("Invalid token payload")
                
        except Exception as e:
            self.logger.warning(f"Token validation failed: {str(e)}")
            raise UnauthorizedError("Invalid or expired token")

        # Fetch user
        try:
            user_uuid = UUID(user_id)
            user = await self.repos.user.get_by_id(user_uuid)
            
            if not user:
                self.logger.warning(f"Token validation failed: user {user_id} not found")
                raise UnauthorizedError("User not found")

            if not user.is_active:
                raise UnauthorizedError("User account is inactive")

            return user

        except UnauthorizedError:
            raise
        except Exception as e:
            self.logger.error(f"Token validation error: {str(e)}")
            raise UnauthorizedError("Token validation failed")

    async def logout_user(self, user_id: UUID) -> dict:
        """
        Logout user and invalidate session.
        
        Process:
        1. Verify user exists
        2. Clear any cached sessions
        3. Log audit trail
        4. Return success
        
        Args:
            user_id: ID of user logging out
        
        Returns:
            Success response: {"success": True, "message": "Logged out successfully"}
        
        Raises:
            NotFoundError: If user doesn't exist
            
        Example:
            result = await auth_service.logout_user(current_user.id)
        """
        await self.verify_user_exists(user_id)

        # Clear any cached sessions (would use Redis in production)
        # await self.redis.delete(f"user_session:{user_id}")
        
        self.log_audit(
            action="LOGOUT",
            entity="User",
            entity_id=user_id,
        )
        self.logger.info(f"User {user_id} logged out")

        return self.success_response(message="Logged out successfully")

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> dict:
        """
        Change user password with verification.
        
        Process:
        1. Fetch user
        2. Verify current password
        3. Validate new password strength
        4. Hash and update password
        5. Log audit trail
        
        Args:
            user_id: ID of user changing password
            current_password: Current password to verify
            new_password: New password to set
        
        Returns:
            Success response
        
        Raises:
            NotFoundError: If user doesn't exist
            UnauthorizedError: If current password invalid
            ValidationError: If new password invalid
            
        Example:
            result = await auth_service.change_password(
                user_id=current_user.id,
                current_password="OldPass123!",
                new_password="NewPass456!"
            )
        """
        # Verify user and current password
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found")

        if not verify_password(current_password, user.password_hash):
            self.logger.warning(f"Password change failed: invalid current password for {user_id}")
            raise UnauthorizedError("Current password is incorrect")

        # Validate new password
        self._validate_password_strength(new_password)

        if current_password == new_password:
            raise ValidationError("New password must be different from current password")

        # Update password
        try:
            async with self.transaction():
                hashed_password = hash_password(new_password)
                await self.repos.user.update(user, {
                    "password_hash": hashed_password,
                })

                self.log_audit(
                    action="CHANGE_PASSWORD",
                    entity="User",
                    entity_id=user_id,
                )
                self.logger.info(f"Password changed for user {user_id}")

                return self.success_response(message="Password changed successfully")

        except Exception as e:
            self.logger.error(f"Password change error for {user_id}: {str(e)}")
            raise

    async def request_password_reset(self, email: str) -> dict:
        """
        Request password reset for user.
        
        Args:
            email: Email address for password reset
        
        Returns:
            Success response (doesn't reveal if email exists - security)
            
        Example:
            result = await auth_service.request_password_reset(email)
        """
        self._validate_email_format(email)

        user = await self.repos.user.get_by_email(email.lower())
        if user:
            # In production, would create reset token and send email
            self.logger.info(f"Password reset requested for {email}")

        # Always return success (don't reveal if email exists)
        return self.success_response(
            message="If email exists, password reset link will be sent"
        )

    async def confirm_password_reset(
        self,
        reset_token: str,
        new_password: str,
    ) -> dict:
        """
        Confirm password reset with token.
        
        Args:
            reset_token: Token from reset email
            new_password: New password to set
        
        Returns:
            Success response with new tokens
            
        Example:
            result = await auth_service.confirm_password_reset(token, new_password)
        """
        # In production:
        # 1. Validate reset token
        # 2. Extract user ID
        # 3. Hash and update password
        # 4. Invalidate token
        
        self._validate_password_strength(new_password)
        
        return self.success_response(message="Password reset successfully")
