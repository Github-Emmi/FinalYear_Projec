"""
Base Service Class - Foundation for all service layer operations.

Provides:
- Generic service base with TypeVar
- Repository dependency injection
- Transaction management with async context managers
- Error handling and custom exceptions
- Structured logging with audit trail
- Type hints throughout
"""

import logging
from contextlib import asynccontextmanager
from typing import Generic, TypeVar, Optional, Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    InternalServerError,
)
from app.repositories.factory import RepositoryFactory


# Generic type for service operations
T = TypeVar("T")


class BaseService(Generic[T]):
    """
    Base service class for all domain services.
    
    Provides:
    - Dependency injection of repositories via RepositoryFactory
    - Transaction management (commit/rollback/flush)
    - Structured logging with request context
    - Error handling utilities
    - Type-safe generic operations
    
    Usage:
        class UserService(BaseService[CustomUser]):
            async def get_user(self, user_id: UUID) -> CustomUser:
                user = await self.repos.user.get_by_id(user_id)
                if not user:
                    raise NotFoundError("User not found")
                self.logger.info(f"Retrieved user {user_id}")
                return user
    """

    def __init__(self, repos: RepositoryFactory) -> None:
        """
        Initialize base service with repository factory.
        
        Args:
            repos: RepositoryFactory instance for data access
        """
        self.repos = repos
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """
        Setup structured logger for this service.
        
        Returns:
            Configured logger instance
        """
        logger_name = self.__class__.__module__ + "." + self.__class__.__name__
        logger = logging.getLogger(logger_name)
        
        if not logger.handlers:
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger

    @asynccontextmanager
    async def transaction(self):
        """
        Async context manager for transaction handling.
        
        Automatically commits on success, rolls back on error.
        
        Usage:
            async with self.transaction():
                await self.repos.user.create(user_data)
                await self.repos.student.create(student_data)
                # Both operations committed together or both rolled back
        
        Raises:
            Exception: Re-raises any exception after rollback
        """
        try:
            yield
            await self.repos.commit()
            self.logger.debug("Transaction committed successfully")
        except Exception as e:
            await self.repos.rollback()
            self.logger.error(f"Transaction rolled back: {str(e)}")
            raise

    async def flush(self) -> None:
        """
        Flush pending changes to database without commit.
        
        Useful for:
        - Getting auto-generated IDs before nested operations
        - Validating constraints before final commit
        
        Usage:
            user = await self.repos.user.create(user_data)
            await self.flush()  # Get the user ID
            user_id = user.id
        """
        await self.repos.flush()
        self.logger.debug("Database session flushed")

    async def commit(self) -> None:
        """
        Commit current transaction to database.
        
        Usage:
            await self.repos.user.create(user_data)
            await self.commit()
        """
        await self.repos.commit()
        self.logger.debug("Transaction committed")

    async def rollback(self) -> None:
        """
        Rollback current transaction (undo pending changes).
        
        Usage:
            try:
                await self.repos.user.create(user_data)
                await self.commit()
            except Exception:
                await self.rollback()
        """
        await self.repos.rollback()
        self.logger.debug("Transaction rolled back")

    # Error handling utility methods

    def _validate_required_field(
        self, value: Any, field_name: str, value_type: type = str
    ) -> None:
        """
        Validate that a required field has a value.
        
        Args:
            value: Field value to validate
            field_name: Name of field for error message
            value_type: Expected type of value
        
        Raises:
            ValidationError: If value is None, empty, or wrong type
        
        Usage:
            self._validate_required_field(email, "email")
        """
        if value is None:
            raise ValidationError(f"{field_name} is required")
        
        if isinstance(value, str) and not value.strip():
            raise ValidationError(f"{field_name} cannot be empty")
        
        if not isinstance(value, value_type):
            raise ValidationError(f"{field_name} must be a {value_type.__name__}")

    def _validate_email_format(self, email: str) -> None:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
        
        Raises:
            ValidationError: If email format is invalid
        
        Usage:
            self._validate_email_format("user@example.com")
        """
        self._validate_required_field(email, "email")
        
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationError(f"Invalid email format: {email}")
        
        if len(email) > 255:
            raise ValidationError("Email address too long (max 255 characters)")

    def _validate_password_strength(self, password: str) -> None:
        """
        Validate password meets strength requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (!@#$%^&*)
        
        Args:
            password: Password to validate
        
        Raises:
            ValidationError: If password doesn't meet requirements
        
        Usage:
            self._validate_password_strength(password)
        """
        self._validate_required_field(password, "password")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        if not any(c.isupper() for c in password):
            raise ValidationError("Password must contain uppercase letter")
        
        if not any(c.islower() for c in password):
            raise ValidationError("Password must contain lowercase letter")
        
        if not any(c.isdigit() for c in password):
            raise ValidationError("Password must contain digit")
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            raise ValidationError(f"Password must contain special character ({special_chars})")

    def _validate_field_length(
        self, value: str, field_name: str, min_len: int = 1, max_len: int = 255
    ) -> None:
        """
        Validate string field length.
        
        Args:
            value: Field value to validate
            field_name: Name of field for error message
            min_len: Minimum length (default 1)
            max_len: Maximum length (default 255)
        
        Raises:
            ValidationError: If length is out of range
        
        Usage:
            self._validate_field_length(username, "username", 3, 20)
        """
        self._validate_required_field(value, field_name)
        
        if len(value) < min_len:
            raise ValidationError(
                f"{field_name} must be at least {min_len} characters"
            )
        
        if len(value) > max_len:
            raise ValidationError(
                f"{field_name} must be at most {max_len} characters"
            )

    def _validate_enum_choice(
        self, value: str, field_name: str, allowed_choices: list[str]
    ) -> None:
        """
        Validate field is one of allowed choices.
        
        Args:
            value: Field value to validate
            field_name: Name of field for error message
            allowed_choices: List of valid choices
        
        Raises:
            ValidationError: If value not in allowed choices
        
        Usage:
            self._validate_enum_choice(role, "role", ["ADMIN", "STAFF", "STUDENT"])
        """
        self._validate_required_field(value, field_name)
        
        if value not in allowed_choices:
            raise ValidationError(
                f"{field_name} must be one of: {', '.join(allowed_choices)}"
            )

    # Logging utilities

    def log_audit(
        self,
        action: str,
        entity: str,
        entity_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        changes: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
    ) -> None:
        """
        Log audit trail for compliance and debugging.
        
        Args:
            action: Action performed (CREATE, UPDATE, DELETE, LOGIN, etc.)
            entity: Entity type (User, Student, Quiz, etc.)
            entity_id: ID of affected entity
            user_id: ID of user performing action
            changes: Dictionary of changes made
            status: Status (SUCCESS, FAILURE, etc.)
        
        Usage:
            self.log_audit(
                action="CREATE",
                entity="User",
                entity_id=user.id,
                user_id=current_user.id,
                changes={"email": "new@example.com"},
            )
        """
        msg = f"AUDIT | {status} | {action} {entity}"
        if entity_id:
            msg += f" #{entity_id}"
        if user_id:
            msg += f" by User#{user_id}"
        if changes:
            msg += f" | Changes: {changes}"
        
        if status == "FAILURE":
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    # Response formatting utilities

    @staticmethod
    def success_response(
        message: str = "Operation successful",
        data: Optional[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Format successful response.
        
        Args:
            message: Success message
            data: Response data
            **kwargs: Additional fields to include
        
        Returns:
            Formatted response dictionary
        
        Usage:
            return self.success_response("User created", user)
        """
        response = {
            "success": True,
            "message": message,
        }
        if data is not None:
            response["data"] = data
        response.update(kwargs)
        return response

    @staticmethod
    def error_response(
        message: str = "Operation failed",
        error_code: Optional[str] = None,
        details: Optional[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Format error response.
        
        Args:
            message: Error message
            error_code: Machine-readable error code
            details: Additional error details
            **kwargs: Additional fields to include
        
        Returns:
            Formatted error response dictionary
        
        Usage:
            return self.error_response("Validation failed", "INVALID_EMAIL")
        """
        response = {
            "success": False,
            "message": message,
        }
        if error_code:
            response["error_code"] = error_code
        if details is not None:
            response["details"] = details
        response.update(kwargs)
        return response

    async def verify_user_exists(self, user_id: UUID) -> None:
        """
        Verify user exists in database.
        
        Args:
            user_id: User ID to verify
        
        Raises:
            NotFoundError: If user doesn't exist
        
        Usage:
            await self.verify_user_exists(user_id)
        """
        exists = await self.repos.user.exists(user_id)
        if not exists:
            raise NotFoundError(f"User #{user_id} not found")

    async def verify_owner_access(
        self, resource_owner_id: UUID, user_id: UUID, resource_name: str = "resource"
    ) -> None:
        """
        Verify user owns resource (for self-service operations).
        
        Args:
            resource_owner_id: ID of resource owner
            user_id: ID of user trying to access
            resource_name: Name of resource for error message
        
        Raises:
            ForbiddenError: If user is not the owner
        
        Usage:
            await self.verify_owner_access(student.user_id, current_user.id, "student profile")
        """
        if resource_owner_id != user_id:
            raise ForbiddenError(f"You do not have access to this {resource_name}")

    async def verify_admin_access(self, user_role: str) -> None:
        """
        Verify user has admin access.
        
        Args:
            user_role: User's role
        
        Raises:
            ForbiddenError: If user is not an admin
        
        Usage:
            await self.verify_admin_access(current_user.role)
        """
        if user_role != "ADMIN":
            raise ForbiddenError("Admin access required")

    async def verify_staff_or_admin_access(self, user_role: str) -> None:
        """
        Verify user is staff or admin.
        
        Args:
            user_role: User's role
        
        Raises:
            ForbiddenError: If user is not staff or admin
        
        Usage:
            await self.verify_staff_or_admin_access(current_user.role)
        """
        if user_role not in ("ADMIN", "STAFF"):
            raise ForbiddenError("Staff or admin access required")
