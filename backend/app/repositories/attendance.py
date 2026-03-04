"""
Attendance Repository - Attendance tracking and reporting
"""

from typing import Optional, List
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.attendance import Attendance
from app.repositories.base import BaseRepository


class AttendanceRepository(BaseRepository[Attendance]):
    """
    Specialized repository for Attendance-specific operations.
    Handles attendance tracking, reporting, and statistics.
    """
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Attendance)
    
    # ==================== STUDENT QUERIES ====================
    async def get_student_attendance(
        self,
        student_id: UUID,
        session_year_id: Optional[UUID] = None
    ) -> List[Attendance]:
        """
        Get attendance records for a student.
        
        Args:
            student_id: Student UUID
            session_year_id: Optional filter by session
            
        Returns:
            List of attendance records
        """
        conditions = [
            Attendance.student_id == student_id,
            Attendance.is_deleted == False
        ]
        
        if session_year_id:
            conditions.append(Attendance.session_year_id == session_year_id)
        
        query = select(Attendance).where(
            and_(*conditions)
        ).order_by(Attendance.attendance_date.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_student_attendance_by_date_range(
        self,
        student_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[Attendance]:
        """
        Get attendance records for a student within date range.
        
        Args:
            student_id: Student UUID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of attendance records
        """
        query = select(Attendance).where(
            and_(
                Attendance.student_id == student_id,
                Attendance.attendance_date >= start_date,
                Attendance.attendance_date <= end_date,
                Attendance.is_deleted == False
            )
        ).order_by(Attendance.attendance_date.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== CLASS QUERIES ====================
    async def get_class_attendance_on_date(
        self,
        class_id: UUID,
        attendance_date: date
    ) -> List[Attendance]:
        """
        Get all attendance records for a class on a specific date.
        
        Args:
            class_id: Class UUID
            attendance_date: Date to query
            
        Returns:
            List of attendance records
        """
        query = select(Attendance).where(
            and_(
                Attendance.class_id == class_id,
                Attendance.attendance_date == attendance_date,
                Attendance.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_class_attendance_by_date_range(
        self,
        class_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[Attendance]:
        """
        Get class attendance within date range.
        
        Args:
            class_id: Class UUID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of attendance records
        """
        query = select(Attendance).where(
            and_(
                Attendance.class_id == class_id,
                Attendance.attendance_date >= start_date,
                Attendance.attendance_date <= end_date,
                Attendance.is_deleted == False
            )
        ).order_by(Attendance.attendance_date.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== STATUS QUERIES ====================
    async def count_by_status(
        self,
        student_id: UUID,
        status: str,
        session_year_id: Optional[UUID] = None
    ) -> int:
        """
        Count attendance records by status for a student.
        
        Args:
            student_id: Student UUID
            status: Attendance status (PRESENT, ABSENT, LATE, EXCUSED)
            session_year_id: Optional session filter
            
        Returns:
            Count of records with that status
        """
        conditions = [
            Attendance.student_id == student_id,
            Attendance.status == status,
            Attendance.is_deleted == False
        ]
        
        if session_year_id:
            conditions.append(Attendance.session_year_id == session_year_id)
        
        count_query = select(func.count(Attendance.id)).where(and_(*conditions))
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    # ==================== CALCULATIONS ====================
    async def calculate_attendance_percentage(
        self,
        student_id: UUID,
        session_year_id: UUID
    ) -> float:
        """
        Calculate attendance percentage for a student in a session.
        
        Args:
            student_id: Student UUID
            session_year_id: Session year UUID
            
        Returns:
            Attendance percentage (0-100)
        """
        # Count present (full) and late (0.75 credit)
        present_count = await self.count_by_status(
            student_id,
            "PRESENT",
            session_year_id
        )
        late_count = await self.count_by_status(
            student_id,
            "LATE",
            session_year_id
        )
        
        # Count total classes
        total_query = select(func.count(Attendance.id)).where(
            and_(
                Attendance.student_id == student_id,
                Attendance.session_year_id == session_year_id,
                Attendance.is_deleted == False
            )
        )
        total = await self.db_session.scalar(total_query)
        
        if not total or total == 0:
            return 0.0
        
        # Calculate: PRESENT + (LATE * 0.75)
        days_attended = present_count + (late_count * 0.75)
        percentage = (days_attended / total) * 100
        
        return round(percentage, 2)
    
    async def get_class_attendance_statistics(
        self,
        class_id: UUID,
        attendance_date: date
    ) -> dict:
        """
        Get attendance statistics for a class on a date.
        
        Args:
            class_id: Class UUID
            attendance_date: Date to analyze
            
        Returns:
            Dictionary with statistics
        """
        records = await self.get_class_attendance_on_date(class_id, attendance_date)
        
        if not records:
            return {
                "total_students": 0,
                "present": 0,
                "absent": 0,
                "late": 0,
                "excused": 0,
                "present_percentage": 0.0
            }
        
        present = len([r for r in records if r.status == "PRESENT"])
        absent = len([r for r in records if r.status == "ABSENT"])
        late = len([r for r in records if r.status == "LATE"])
        excused = len([r for r in records if r.status == "EXCUSED"])
        total = len(records)
        
        return {
            "total_students": total,
            "present": present,
            "absent": absent,
            "late": late,
            "excused": excused,
            "present_percentage": round((present / total) * 100, 2) if total else 0.0
        }
    
    # ==================== TRENDS ====================
    async def get_chronic_absentees(
        self,
        class_id: UUID,
        session_year_id: UUID,
        threshold_percentage: float = 20.0
    ) -> List[tuple[UUID, float]]:
        """
        Get students with high absence rates.
        
        Args:
            class_id: Class UUID
            session_year_id: Session year UUID
            threshold_percentage: Maximum allowed absence %
            
        Returns:
            List of tuples (student_id, absence_percentage)
        """
        # This would need student-specific logic
        # Implementation depends on accessing each student's attendance
        return []
