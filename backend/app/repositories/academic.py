"""
Academic Repository - Academic structure queries (SessionYear, Department, Class, Subject, TimeTable)
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.academic import SessionYear, Department, Class, Subject, TimeTable
from app.repositories.base import BaseRepository


class SessionYearRepository(BaseRepository[SessionYear]):
    """Repository for SessionYear queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, SessionYear)
    
    async def get_active_session(self) -> Optional[SessionYear]:
        """Get the currently active session year."""
        query = select(SessionYear).where(
            and_(
                SessionYear.is_active == True,
                SessionYear.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_by_name(self, name: str) -> Optional[SessionYear]:
        """Get session by name (e.g., '2023/2024')"""
        query = select(SessionYear).where(
            SessionYear.session_name == name
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()


class DepartmentRepository(BaseRepository[Department]):
    """Repository for Department queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Department)
    
    async def get_by_code(self, code: str) -> Optional[Department]:
        """Get department by code."""
        query = select(Department).where(
            Department.code == code
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def search_by_name(
        self,
        name_query: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Department], int]:
        """Search departments by name."""
        search_term = f"%{name_query}%"
        
        query = select(Department).where(
            Department.department_name.ilike(search_term)
        )
        
        count_query = select(func.count(Department.id)).where(
            Department.department_name.ilike(search_term)
        )
        total = await self.db_session.scalar(count_query)
        
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0


class ClassRepository(BaseRepository[Class]):
    """Repository for Class queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Class)
    
    async def get_by_name(self, name: str) -> Optional[Class]:
        """Get class by name."""
        query = select(Class).where(
            Class.class_name == name
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_classes_by_department(
        self,
        department_id: UUID
    ) -> List[Class]:
        """Get all classes in a department."""
        query = select(Class).where(
            and_(
                Class.department_id == department_id,
                Class.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()


class SubjectRepository(BaseRepository[Subject]):
    """Repository for Subject queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Subject)
    
    async def get_by_code(self, code: str) -> Optional[Subject]:
        """Get subject by code."""
        query = select(Subject).where(
            Subject.code == code
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def get_class_subjects(self, class_id: UUID) -> List[Subject]:
        """Get all subjects offered in a class."""
        query = select(Subject).where(
            and_(
                Subject.class_id == class_id,
                Subject.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_staff_subjects(self, staff_id: UUID) -> List[Subject]:
        """Get all subjects taught by a staff member."""
        query = select(Subject).where(
            and_(
                Subject.staff_id == staff_id,
                Subject.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_department_subjects(
        self,
        department_id: UUID
    ) -> List[Subject]:
        """Get all subjects in a department."""
        query = select(Subject).where(
            and_(
                Subject.department_id == department_id,
                Subject.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()


class TimeTableRepository(BaseRepository[TimeTable]):
    """Repository for TimeTable queries"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, TimeTable)
    
    async def get_class_timetable(
        self,
        class_id: UUID,
        session_year_id: UUID
    ) -> List[TimeTable]:
        """Get complete timetable for a class."""
        query = select(TimeTable).where(
            and_(
                TimeTable.class_id == class_id,
                TimeTable.session_year_id == session_year_id,
                TimeTable.is_deleted == False
            )
        ).order_by(TimeTable.day, TimeTable.start_time)
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_staff_timetable(
        self,
        staff_id: UUID,
        session_year_id: UUID
    ) -> List[TimeTable]:
        """Get timetable for a staff member."""
        query = select(TimeTable).where(
            and_(
                TimeTable.staff_id == staff_id,
                TimeTable.session_year_id == session_year_id,
                TimeTable.is_deleted == False
            )
        ).order_by(TimeTable.day, TimeTable.start_time)
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_subject_timetable(
        self,
        subject_id: UUID
    ) -> List[TimeTable]:
        """Get all timetable entries for a subject."""
        query = select(TimeTable).where(
            and_(
                TimeTable.subject_id == subject_id,
                TimeTable.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_day_schedule(
        self,
        class_id: UUID,
        day: str,
        session_year_id: UUID
    ) -> List[TimeTable]:
        """Get schedule for a class on a specific day."""
        query = select(TimeTable).where(
            and_(
                TimeTable.class_id == class_id,
                TimeTable.day == day.upper(),
                TimeTable.session_year_id == session_year_id,
                TimeTable.is_deleted == False
            )
        ).order_by(TimeTable.start_time)
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
