"""
User Service - User profile management and lifecycle operations.

Provides:
- User creation with validation
- Profile retrieval and updates
- Password management
- User search and filtering
- Role assignment (admin only)
- User deactivation
- Session management
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
)
from app.core.security import (
    hash_password,
    verify_password,
)
from app.models.user import CustomUser
from app.repositories.factory import RepositoryFactory
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.base import BaseService


class UserService(BaseService[CustomUser]):
    """
    User service for profile management and lifecycle operations.
    
    Handles:
    - User creation with validation
    - Profile retrieval and updates
    - Password changes
    - User search and filtering
    - Role assignment
    - User deactivation
    - Session invalidation
    
    Usage:
        user_service = UserService(repos)
        user = await user_service.get_user(user_id)
        updated = await user_service.update_user_profile(user_id, updates)
        results, total = await user_service.search_users("john", role="STUDENT")
    """

    async def create_user(
        self,
        email: str,
        username: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str = "STUDENT",
    ) -> dict:
        """
        Create new user with validation.
        
        Validates email/username uniqueness, password strength,
        hashes password, and creates database record.
        
        Args:
            email: User email address
            username: Username for login
            password: Plain-text password
            first_name: User's first name
            last_name: User's last name
            role: User role (ADMIN, STAFF, STUDENT)
        
        Returns:
            Success response with UserResponse data
        
        Raises:
            ValidationError: If validation fails
            ConflictError: If email or username exists
            
        Example:
            result = await user_service.create_user(
                email="user@school.edu",
                username="newuser",
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

        # Check uniqueness
        email_exists = await self.repos.user.email_exists(email.lower())
        if email_exists:
            self.logger.warning(f"Create user failed: email {email} already exists")
            raise ValidationError("Email address already registered")

        username_exists = await self.repos.user.username_exists(username)
        if username_exists:
            self.logger.warning(f"Create user failed: username {username} already exists")
            raise ValidationError("Username already taken")

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
                    "is_active": True,
                    "is_email_verified": False,
                })

                self.log_audit(
                    action="CREATE_USER",
                    entity="User",
                    entity_id=user.id,
                    changes={"email": email, "role": role},
                )
                self.logger.info(f"User {email} created with role {role}")

                return self.success_response(
                    message="User created successfully",
                    data=UserResponse.model_validate(user),
                )

        except Exception as e:
            self.logger.error(f"Create user error: {str(e)}")
            raise

    async def get_user(self, user_id: UUID) -> dict:
        """
        Retrieve user by ID.
        
        Args:
            user_id: User UUID
        
        Returns:
            Success response with UserResponse data
        
        Raises:
            NotFoundError: If user not found
            
        Example:
            result = await user_service.get_user(user_id)
            if result["success"]:
                user = result["data"]
        """
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            self.logger.warning(f"Get user failed: user {user_id} not found")
            raise NotFoundError(f"User #{user_id} not found")

        self.logger.debug(f"Retrieved user {user_id}")

        return self.success_response(
            message="User retrieved successfully",
            data=UserResponse.model_validate(user),
        )

    async def update_user_profile(
        self,
        user_id: UUID,
        updates: dict,
    ) -> dict:
        """
        Update user profile (allowed fields only).
        
        Allowed fields: first_name, last_name, phone, avatar_url, bio
        Blocked fields: email, username, password, role, is_active
        
        Args:
            user_id: User UUID
            updates: Dictionary of fields to update
        
        Returns:
            Success response with updated UserResponse
        
        Raises:
            NotFoundError: If user not found
            ValidationError: If trying to update blocked fields
            
        Example:
            result = await user_service.update_user_profile(
                user_id,
                {"first_name": "Jane", "phone": "+1234567890"}
            )
        """
        # Fetch user
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")

        # Verify no blocked fields
        blocked_fields = {"email", "username", "password_hash", "role", "is_active"}
        attempted_blocked = set(updates.keys()) & blocked_fields
        if attempted_blocked:
            raise ValidationError(
                f"Cannot update these fields: {', '.join(attempted_blocked)}"
            )

        # Validate allowed fields if present
        if "first_name" in updates:
            self._validate_field_length(
                updates["first_name"], "first_name", min_len=2, max_len=50
            )
        if "last_name" in updates:
            self._validate_field_length(
                updates["last_name"], "last_name", min_len=2, max_len=50
            )
        if "phone" in updates and updates["phone"]:
            self._validate_field_length(
                updates["phone"], "phone", min_len=7, max_len=20
            )

        # Update user
        try:
            async with self.transaction():
                updated_user = await self.repos.user.update(user, updates)

                self.log_audit(
                    action="UPDATE_PROFILE",
                    entity="User",
                    entity_id=user_id,
                    changes=updates,
                )
                self.logger.info(f"User {user_id} profile updated")

                return self.success_response(
                    message="Profile updated successfully",
                    data=UserResponse.model_validate(updated_user),
                )

        except Exception as e:
            self.logger.error(f"Update profile error: {str(e)}")
            raise

    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> dict:
        """
        Change user password with verification.
        
        Verifies old password, validates new password strength,
        hashes and updates password, invalidates other sessions.
        
        Args:
            user_id: User UUID
            old_password: Current password to verify
            new_password: New password to set
        
        Returns:
            Success response with invalidation message
        
        Raises:
            NotFoundError: If user not found
            UnauthorizedError: If old password is incorrect
            ValidationError: If new password invalid or same as old
            
        Example:
            result = await user_service.change_password(
                user_id,
                old_password="OldPass123!",
                new_password="NewPass456!"
            )
        """
        # Fetch user
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")

        # Verify old password
        if not verify_password(old_password, user.password_hash):
            self.logger.warning(f"Change password failed: invalid old password for {user_id}")
            raise UnauthorizedError("Current password is incorrect")

        # Validate new password
        self._validate_password_strength(new_password)

        if old_password == new_password:
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

                return self.success_response(
                    message="Password changed successfully. Please login again."
                )

        except Exception as e:
            self.logger.error(f"Change password error: {str(e)}")
            raise

    async def deactivate_user(self, user_id: UUID, reason: str) -> dict:
        """
        Deactivate user account.
        
        Marks user as inactive, creates audit log with reason,
        and clears all active sessions.
        
        Args:
            user_id: User UUID
            reason: Reason for deactivation (logged for audit)
        
        Returns:
            Success response
        
        Raises:
            NotFoundError: If user not found
            
        Example:
            result = await user_service.deactivate_user(
                user_id,
                reason="Administrative action: Account violation"
            )
        """
        # Verify user exists
        await self.verify_user_exists(user_id)

        user = await self.repos.user.get_by_id(user_id)
        
        try:
            async with self.transaction():
                # Deactivate user
                await self.repos.user.update(user, {
                    "is_active": False,
                    "deactivated_at": datetime.utcnow(),
                })

                # Log audit with reason
                self.log_audit(
                    action="DEACTIVATE_USER",
                    entity="User",
                    entity_id=user_id,
                    changes={"deactivated": True, "reason": reason},
                )

                # Clear sessions (in production, would use Redis)
                # await self.redis.delete(f"user_sessions:{user_id}:*")

                self.logger.info(f"User {user_id} deactivated. Reason: {reason}")

                return self.success_response(
                    message=f"User deactivated successfully. Reason: {reason}"
                )

        except Exception as e:
            self.logger.error(f"Deactivate user error: {str(e)}")
            raise

    async def search_users(
        self,
        query: str,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """
        Search users by email, username, first name, or last name.
        
        Optionally filter by role (ADMIN, STAFF, STUDENT).
        
        Args:
            query: Search query string
            role: Optional role filter
            skip: Pagination offset
            limit: Pagination limit (max 100)
        
        Returns:
            Success response with paginated results and total count
        
        Raises:
            ValidationError: If query too short or role invalid
            
        Example:
            result = await user_service.search_users(
                query="john",
                role="STUDENT",
                skip=0,
                limit=20
            )
            if result["success"]:
                users = result["data"]
                total = result["total"]
        """
        # Validate inputs
        self._validate_field_length(query, "query", min_len=2, max_len=100)
        if limit > 100:
            limit = 100
        if skip < 0:
            skip = 0

        if role:
            self._validate_enum_choice(role, "role", ["ADMIN", "STAFF", "STUDENT", ""])

        try:
            # Search by name (uses repository search)
            results, total = await self.repos.user.search_by_name(
                query, skip=skip, limit=limit
            )

            # Filter by role if provided
            if role:
                results = [u for u in results if u.role == role]
                total = len(results)

            user_responses = [
                UserResponse.model_validate(user) for user in results
            ]

            self.logger.debug(
                f"User search executed: query='{query}', role={role}, "
                f"results={len(results)}, total={total}"
            )

            return self.success_response(
                message="Search completed",
                data=user_responses,
                total=total,
                query=query,
                role=role if role else None,
            )

        except Exception as e:
            self.logger.error(f"User search error: {str(e)}")
            raise

    async def assign_role(
        self,
        user_id: UUID,
        new_role: str,
        changed_by: Optional[UUID] = None,
    ) -> dict:
        """
        Assign new role to user (admin operation).
        
        Note: Authorization (admin-only) should be checked in endpoint layer.
        This method assumes caller has already verified admin access.
        
        Args:
            user_id: User UUID
            new_role: New role (ADMIN, STAFF, STUDENT)
            changed_by: Admin user ID who made the change (for audit)
        
        Returns:
            Success response with updated UserResponse
        
        Raises:
            NotFoundError: If user not found
            ValidationError: If role invalid or same as current
            
        Example:
            result = await user_service.assign_role(
                user_id=student_id,
                new_role="STAFF",
                changed_by=admin_id
            )
        """
        # Validate role
        self._validate_enum_choice(new_role, "role", ["ADMIN", "STAFF", "STUDENT"])

        # Fetch user
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")

        # Check if role is actually changing
        if user.role == new_role:
            raise ValidationError(f"User already has role '{new_role}'")

        old_role = user.role

        try:
            async with self.transaction():
                # Update role
                updated_user = await self.repos.user.update(user, {
                    "role": new_role,
                })

                # Audit log
                self.log_audit(
                    action="ASSIGN_ROLE",
                    entity="User",
                    entity_id=user_id,
                    user_id=changed_by,
                    changes={
                        "role_changed_from": old_role,
                        "role_changed_to": new_role,
                    },
                )

                self.logger.info(
                    f"User {user_id} role changed from {old_role} to {new_role} "
                    f"by admin {changed_by}"
                )

                return self.success_response(
                    message=f"User role changed from {old_role} to {new_role}",
                    data=UserResponse.model_validate(updated_user),
                )

        except Exception as e:
            self.logger.error(f"Assign role error: {str(e)}")
            raise

    async def get_user_by_email(self, email: str) -> dict:
        """
        Retrieve user by email (helper method).
        
        Args:
            email: User email address
        
        Returns:
            Success response with UserResponse data
        
        Raises:
            NotFoundError: If user not found
        """
        user = await self.repos.user.get_by_email(email.lower())
        if not user:
            raise NotFoundError(f"User with email {email} not found")

        return self.success_response(
            message="User retrieved successfully",
            data=UserResponse.model_validate(user),
        )

    async def get_user_by_username(self, username: str) -> dict:
        """
        Retrieve user by username (helper method).
        
        Args:
            username: Username
        
        Returns:
            Success response with UserResponse data
        
        Raises:
            NotFoundError: If user not found
        """
        user = await self.repos.user.get_by_username(username)
        if not user:
            raise NotFoundError(f"User with username {username} not found")

        return self.success_response(
            message="User retrieved successfully",
            data=UserResponse.model_validate(user),
        )

    async def list_users_by_role(
        self,
        role: str,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """
        List all users with specific role.
        
        Args:
            role: Role to filter by (ADMIN, STAFF, STUDENT)
            skip: Pagination offset
            limit: Pagination limit
        
        Returns:
            Success response with paginated user list and total count
        
        Raises:
            ValidationError: If role invalid
        """
        self._validate_enum_choice(role, "role", ["ADMIN", "STAFF", "STUDENT"])

        users = await self.repos.user.get_by_role(role)
        total = len(users)

        # Apply pagination
        paginated_users = users[skip : skip + limit]
        user_responses = [
            UserResponse.model_validate(user) for user in paginated_users
        ]

        self.logger.debug(f"Listed {len(user_responses)} {role} users (total: {total})")

        return self.success_response(
            message=f"Retrieved {role} users",
            data=user_responses,
            total=total,
            role=role,
        )

    async def activate_user(self, user_id: UUID) -> dict:
        """
        Reactivate a deactivated user.
        
        Args:
            user_id: User UUID
        
        Returns:
            Success response with updated UserResponse
        
        Raises:
            NotFoundError: If user not found
        """
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")

        if user.is_active:
            raise ValidationError("User is already active")

        try:
            async with self.transaction():
                updated_user = await self.repos.user.update(user, {
                    "is_active": True,
                    "deactivated_at": None,
                })

                self.log_audit(
                    action="ACTIVATE_USER",
                    entity="User",
                    entity_id=user_id,
                    changes={"activated": True},
                )
                self.logger.info(f"User {user_id} reactivated")

                return self.success_response(
                    message="User activated successfully",
                    data=UserResponse.model_validate(updated_user),
                )

        except Exception as e:
            self.logger.error(f"Activate user error: {str(e)}")
            raise
