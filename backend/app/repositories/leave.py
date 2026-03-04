"""
Leave Repository - Leave request and approval tracking
"""

from typing import Optional, List
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.leave import StudentLeave, StaffLeave
from app.repositories.base import BaseRepository


class StudentLeaveRepository(BaseRepository[StudentLeave]):
    """Repository for Student leave requests"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, StudentLeave)
    
    async def get_by_student(
        self,
        student_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[StudentLeave], int]:
        """Get all leave requests for a student."""
        count_query = select(func.count(StudentLeave.id)).where(
            StudentLeave.student_id == student_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(StudentLeave).where(
            StudentLeave.student_id == student_id
        ).offset(skip).limit(limit).order_by(StudentLeave.start_date.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_pending_requests(self) -> List[StudentLeave]:
        """Get all pending leave requests"""
        query = select(StudentLeave).where(
            StudentLeave.status == "PENDING"
        ).order_by(StudentLeave.requested_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[StudentLeave], int]:
        """Get leave requests by status."""
        count_query = select(func.count(StudentLeave.id)).where(
            StudentLeave.status == status
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(StudentLeave).where(
            StudentLeave.status == status
        ).offset(skip).limit(limit)
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_overlapping_leaves(
        self,
        student_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[StudentLeave]:
        """Get leaves that overlap with given date range."""
        query = select(StudentLeave).where(
            and_(
                StudentLeave.student_id == student_id,
                StudentLeave.start_date <= end_date,
                StudentLeave.end_date >= start_date,
                StudentLeave.status != "REJECTED"
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()


class StaffLeaveRepository(BaseRepository[StaffLeave]):
    """Repository for Staff leave requests"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, StaffLeave)
    
    async def get_by_staff(
        self,
        staff_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[StaffLeave], int]:
        """Get all leave requests for staff."""
        count_query = select(func.count(StaffLeave.id)).where(
            StaffLeave.staff_id == staff_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(StaffLeave).where(
            StaffLeave.staff_id == staff_id
        ).offset(skip).limit(limit).order_by(StaffLeave.start_date.desc())
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_pending_requests(self) -> List[StaffLeave]:
        """Get all pending leave requests"""
        query = select(StaffLeave).where(
            StaffLeave.status == "PENDING"
        ).order_by(StaffLeave.requested_at.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_leave_type(self, leave_type: str) -> List[StaffLeave]:
        """Get leaves by type."""
        query = select(StaffLeave).where(
            StaffLeave.leave_type == leave_type
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_overlapping_leaves(
        self,
        staff_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[StaffLeave]:
        """Get leaves that overlap with given date range."""
        query = select(StaffLeave).where(
            and_(
                StaffLeave.staff_id == staff_id,
                StaffLeave.start_date <= end_date,
                StaffLeave.end_date >= start_date,
                StaffLeave.status == "APPROVED"
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_cover_assignments(
        self,
        cover_staff_id: UUID
    ) -> List[StaffLeave]:
        """Get all leaves where staff is assigned as cover."""
        query = select(StaffLeave).where(
            and_(
                StaffLeave.cover_staff_id == cover_staff_id,
                StaffLeave.status == "APPROVED"
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
