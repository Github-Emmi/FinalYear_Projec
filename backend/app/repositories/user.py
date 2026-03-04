"""
User Repository - Authentication and user lookups
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.user import CustomUser
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[CustomUser]):
    """
    Specialized repository for User-specific operations.
    Handles authentication, lookups by email/username, and role-based queries.
    """
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, CustomUser)
    
    # ==================== AUTHENTICATION ====================
    async def get_by_email(self, email: str) -> Optional[CustomUser]:
        """
        Find user by email (primary for login).
        
        Args:
            email: User email address
            
        Returns:
            CustomUser instance or None if not found
            
        Example:
            user = await user_repo.get_by_email("john@school.com")
            if user:
                # Verify password
                # Create JWT token
        """
        query = select(CustomUser).where(
            CustomUser.email == email.lower()  # Case-insensitive
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_by_username(self, username: str) -> Optional[CustomUser]:
        """
        Find user by username.
        
        Args:
            username: User username
            
        Returns:
            CustomUser instance or None if not found
        """
        query = select(CustomUser).where(
            CustomUser.username == username.lower()  # Case-insensitive
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def email_exists(self, email: str) -> bool:
        """
        Check if email is already registered.
        
        Args:
            email: Email to check
            
        Returns:
            True if exists, False otherwise
        """
        user = await self.get_by_email(email)
        return user is not None
    
    async def username_exists(self, username: str) -> bool:
        """
        Check if username is already taken.
        
        Args:
            username: Username to check
            
        Returns:
            True if exists, False otherwise
        """
        user = await self.get_by_username(username)
        return user is not None
    
    # ==================== ROLE-BASED QUERIES ====================
    async def get_by_role(self, role: str) -> List[CustomUser]:
        """
        Get all users with specific role.
        
        Args:
            role: User role (ADMIN, STAFF, STUDENT)
            
        Returns:
            List of users with that role
            
        Example:
            admins = await user_repo.get_by_role("ADMIN")
            teachers = await user_repo.get_by_role("STAFF")
        """
        query = select(CustomUser).where(
            and_(
                CustomUser.role == role,
                CustomUser.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_active_users(self) -> List[CustomUser]:
        """
        Get all active (is_active=True, is_deleted=False) users.
        
        Returns:
            List of active users
        """
        query = select(CustomUser).where(
            and_(
                CustomUser.is_active == True,
                CustomUser.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_inactive_users(self) -> List[CustomUser]:
        """
        Get all inactive (is_active=False) users.
        
        Returns:
            List of inactive users
        """
        query = select(CustomUser).where(
            CustomUser.is_active == False
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== SEARCH ====================
    async def search_by_name(
        self,
        name_query: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[CustomUser], int]:
        """
        Search users by first or last name.
        
        Args:
            name_query: Name to search for
            skip: Pagination skip
            limit: Pagination limit
            
        Returns:
            Tuple of (matching users, total count)
        """
        search_term = f"%{name_query}%"
        
        query = select(CustomUser).where(
            and_(
                (CustomUser.first_name.ilike(search_term)) |
                (CustomUser.last_name.ilike(search_term)),
                CustomUser.is_deleted == False
            )
        )
        
        # Get total count
        count_query = select(func.count(CustomUser.id)).where(
            and_(
                (CustomUser.first_name.ilike(search_term)) |
                (CustomUser.last_name.ilike(search_term)),
                CustomUser.is_deleted == False
            )
        )
        total = await self.db_session.scalar(count_query)
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    # ==================== UPDATE VERIFICATION ====================
    async def mark_verified(self, user_id: UUID) -> bool:
        """
        Mark user email as verified.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if successful, False if user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_verified = True
        await self.db_session.commit()
        return True
    
    async def mark_unverified(self, user_id: UUID) -> bool:
        """Mark user email as unverified."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_verified = False
        await self.db_session.commit()
        return True
    
    # ==================== ACTIVITY TRACKING ====================
    async def update_last_login(self, user_id: UUID) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if successful, False if user not found
        """
        from datetime import datetime
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.last_login = datetime.utcnow()
        await self.db_session.commit()
        return True
    
    async def deactivate_user(self, user_id: UUID) -> bool:
        """
        Deactivate user account.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if successful, False if user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        await self.db_session.commit()
        return True
    
    async def activate_user(self, user_id: UUID) -> bool:
        """Activate user account."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = True
        await self.db_session.commit()
        return True


# Import func for count queries
from sqlalchemy import func
