"""
Student Repository - Student profile and enrollment queries
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.student import Student
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    """
    Specialized repository for Student-specific operations.
    Handles enrollment, class filtering, and student-specific searches.
    """
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Student)
    
    # ==================== CLASS-BASED QUERIES ====================
    async def get_by_class(
        self,
        class_id: UUID,
        session_year_id: Optional[UUID] = None
    ) -> List[Student]:
        """
        Get all students enrolled in a specific class.
        
        Args:
            class_id: Class UUID
            session_year_id: Optional session year filter
            
        Returns:
            List of students in that class
            
        Example:
            students = await student_repo.get_by_class(class_id)
            # Returns: All 30 students in Form 1A
        """
        conditions = [
            Student.class_id == class_id,
            Student.status == "ACTIVE",
            Student.is_deleted == False
        ]
        
        if session_year_id:
            conditions.append(Student.session_year_id == session_year_id)
        
        query = select(Student).where(and_(*conditions))
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_department(
        self,
        department_id: UUID,
        session_year_id: Optional[UUID] = None
    ) -> List[Student]:
        """
        Get all students in a specific department.
        
        Args:
            department_id: Department UUID
            session_year_id: Optional session year filter
            
        Returns:
            List of students in that department
        """
        conditions = [
            Student.department_id == department_id,
            Student.is_deleted == False
        ]
        
        if session_year_id:
            conditions.append(Student.session_year_id == session_year_id)
        
        query = select(Student).where(and_(*conditions))
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_by_session(self, session_year_id: UUID) -> List[Student]:
        """
        Get all enrolled students for a session year.
        
        Args:
            session_year_id: Session year UUID
            
        Returns:
            List of students in that session
        """
        query = select(Student).where(
            and_(
                Student.session_year_id == session_year_id,
                Student.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== SEARCH ====================
    async def search(
        self,
        query_text: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Student], int]:
        """
        Full-text search for students by name or admission number.
        
        Args:
            query_text: Search term
            skip: Pagination skip
            limit: Pagination limit
            
        Returns:
            Tuple of (matching students, total count)
            
        Example:
            students, total = await student_repo.search("Ahmed", skip=0, limit=10)
            # Returns: All students named "Ahmed" (paginated)
        """
        search_term = f"%{query_text}%"
        
        # Build query
        search_condition = and_(
            (Student.first_name.ilike(search_term)) |
            (Student.last_name.ilike(search_term)) |
            (Student.admission_number.ilike(search_term)),
            Student.is_deleted == False
        )
        
        query = select(Student).where(search_condition)
        
        # Get total count
        count_query = select(func.count(Student.id)).where(search_condition)
        total = await self.db_session.scalar(count_query)
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    # ==================== PERFORMANCE/RANKING ====================
    async def get_high_performers(
        self,
        class_id: UUID,
        min_gpa: float = 3.5
    ) -> List[Student]:
        """
        Get top students in a class by GPA.
        
        Args:
            class_id: Class UUID
            min_gpa: Minimum GPA threshold
            
        Returns:
            List of students above GPA threshold
            
        Example:
            top_students = await student_repo.get_high_performers(
                class_id=uuid,
                min_gpa=3.5
            )
        """
        query = select(Student).where(
            and_(
                Student.class_id == class_id,
                Student.gpa >= min_gpa,
                Student.status == "ACTIVE",
                Student.is_deleted == False
            )
        ).order_by(Student.gpa.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_low_performers(
        self,
        class_id: UUID,
        max_gpa: float = 2.0
    ) -> List[Student]:
        """
        Get students with low GPA (needs support).
        
        Args:
            class_id: Class UUID
            max_gpa: Maximum GPA threshold
            
        Returns:
            List of students below GPA threshold
        """
        query = select(Student).where(
            and_(
                Student.class_id == class_id,
                Student.gpa <= max_gpa,
                Student.status == "ACTIVE",
                Student.is_deleted == False
            )
        ).order_by(Student.gpa.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== STATUS QUERIES ====================
    async def get_active_students(self, session_year_id: UUID) -> List[Student]:
        """
        Get all active (enrolled, not withdrawn) students for current session.
        
        Args:
            session_year_id: Session year UUID
            
        Returns:
            List of active students
        """
        query = select(Student).where(
            and_(
                Student.session_year_id == session_year_id,
                Student.status == "ACTIVE",
                Student.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_withdrawn_students(self, session_year_id: UUID) -> List[Student]:
        """Get all withdrawn students for a session."""
        query = select(Student).where(
            and_(
                Student.session_year_id == session_year_id,
                Student.status == "WITHDRAWN",
                Student.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_graduated_students(self, session_year_id: UUID) -> List[Student]:
        """Get all graduated students for a session."""
        query = select(Student).where(
            and_(
                Student.session_year_id == session_year_id,
                Student.status == "GRADUATED",
                Student.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== STATISTICS ====================
    async def count_by_class(self, class_id: UUID) -> int:
        """
        Count total students in a class.
        
        Args:
            class_id: Class UUID
            
        Returns:
            Number of students in class
        """
        count_query = select(func.count(Student.id)).where(
            and_(
                Student.class_id == class_id,
                Student.is_deleted == False
            )
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    async def count_by_status(
        self,
        session_year_id: UUID,
        status: str
    ) -> int:
        """
        Count students by status in a session.
        
        Args:
            session_year_id: Session year UUID
            status: Student status (ACTIVE, WITHDRAWN, GRADUATED)
            
        Returns:
            Number of students with that status
        """
        count_query = select(func.count(Student.id)).where(
            and_(
                Student.session_year_id == session_year_id,
                Student.status == status,
                Student.is_deleted == False
            )
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    # ==================== USER LINKING ====================
    async def get_by_user(self, user_id: UUID) -> Optional[Student]:
        """
        Get student profile for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Student instance or None if not found
        """
        query = select(Student).where(
            and_(
                Student.user_id == user_id,
                Student.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
