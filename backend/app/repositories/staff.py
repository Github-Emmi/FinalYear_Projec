"""
Staff Repository - Staff and administrative personnel queries
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.staff import Staff, AdminHOD
from app.repositories.base import BaseRepository


class StaffRepository(BaseRepository[Staff]):
    """Repository for Staff queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Staff)
    
    async def get_by_user(self, user_id: UUID) -> Optional[Staff]:
        """Get staff profile for a user."""
        query = select(Staff).where(
            and_(
                Staff.user_id == user_id,
                Staff.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_by_department(self, department_id: UUID) -> List[Staff]:
        """Get all staff in a department."""
        query = select(Staff).where(
            and_(
                Staff.department_id == department_id,
                Staff.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_session(self, session_year_id: UUID) -> List[Staff]:
        """Get all staff for a session year."""
        query = select(Staff).where(
            and_(
                Staff.session_year_id == session_year_id,
                Staff.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def search_by_name(
        self,
        name_query: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Staff], int]:
        """Search staff by name."""
        search_term = f"%{name_query}%"
        
        # This requires joining with User table
        from app.models.user import CustomUser
        
        query = select(Staff).where(
            Staff.is_deleted == False
        )
        
        count_query = select(func.count(Staff.id)).where(
            Staff.is_deleted == False
        )
        total = await self.db_session.scalar(count_query)
        
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def count_by_qualifications(self, qualification: str) -> int:
        """Count staff with specific qualification."""
        count_query = select(func.count(Staff.id)).where(
            and_(
                Staff.qualification == qualification,
                Staff.is_deleted == False
            )
        )
        total = await self.db_session.scalar(count_query)
        return total or 0


class AdminHODRepository(BaseRepository[AdminHOD]):
    """Repository for Admin/HOD queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, AdminHOD)
    
    async def get_by_user(self, user_id: UUID) -> Optional[AdminHOD]:
        """Get admin/HOD profile for a user."""
        query = select(AdminHOD).where(
            and_(
                AdminHOD.user_id == user_id,
                AdminHOD.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_department_hod(self, department_id: UUID) -> Optional[AdminHOD]:
        """Get HOD for a department."""
        query = select(AdminHOD).where(
            and_(
                AdminHOD.department_id == department_id,
                AdminHOD.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_admins(self) -> List[AdminHOD]:
        """Get all principal/admin users."""
        query = select(AdminHOD).where(
            and_(
                AdminHOD.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_title(self, title: str) -> List[AdminHOD]:
        """Get admin/HOD by title."""
        query = select(AdminHOD).where(
            and_(
                AdminHOD.title == title,
                AdminHOD.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
