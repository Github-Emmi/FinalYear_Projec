"""
Assignment Repository - Assignment submission and grading queries
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.assignment import Assignment, AssignmentSubmission
from app.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[Assignment]):
    """
    Specialized repository for Assignment-specific operations.
    Handles assignment filtering, deadline tracking, and submission queries.
    """
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Assignment)
    
    # ==================== CLASS-BASED QUERIES ====================
    async def get_class_assignments(self, class_id: UUID) -> List[Assignment]:
        """
        Get all assignments for a class.
        
        Args:
            class_id: Class UUID
            
        Returns:
            List of assignments
        """
        query = select(Assignment).where(
            and_(
                Assignment.class_id == class_id,
                Assignment.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_subject_assignments(self, subject_id: UUID) -> List[Assignment]:
        """
        Get all assignments for a subject.
        
        Args:
            subject_id: Subject UUID
            
        Returns:
            List of assignments
        """
        query = select(Assignment).where(
            and_(
                Assignment.subject_id == subject_id,
                Assignment.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== TIME-BASED QUERIES ====================
    async def get_overdue_assignments(self) -> List[Assignment]:
        """
        Get assignments past due date.
        
        Returns:
            List of overdue assignments
        """
        now = datetime.utcnow()
        query = select(Assignment).where(
            and_(
                Assignment.due_date < now,
                Assignment.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_active_assignments(self, class_id: UUID) -> List[Assignment]:
        """
        Get currently active assignments (not yet due).
        
        Args:
            class_id: Class UUID
            
        Returns:
            List of active assignments
        """
        now = datetime.utcnow()
        query = select(Assignment).where(
            and_(
                Assignment.class_id == class_id,
                Assignment.due_date >= now,
                Assignment.is_deleted == False
            )
        ).order_by(Assignment.due_date.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_upcoming_assignments(self, class_id: UUID) -> List[Assignment]:
        """
        Get upcoming assignments (due in future).
        
        Args:
            class_id: Class UUID
            
        Returns:
            List of future assignments
        """
        now = datetime.utcnow()
        query = select(Assignment).where(
            and_(
                Assignment.class_id == class_id,
                Assignment.due_date > now,
                Assignment.is_deleted == False
            )
        ).order_by(Assignment.due_date.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== SUBMISSION QUERIES ====================
    async def get_submissions(
        self,
        assignment_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[AssignmentSubmission], int]:
        """
        Get all submissions for an assignment with pagination.
        
        Args:
            assignment_id: Assignment UUID
            skip: Pagination skip
            limit: Pagination limit
            
        Returns:
            Tuple of (submissions, total count)
        """
        count_query = select(func.count(AssignmentSubmission.id)).where(
            AssignmentSubmission.assignment_id == assignment_id
        )
        total = await self.db_session.scalar(count_query)
        
        query = select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id
        ).offset(skip).limit(limit)
        
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_student_submission(
        self,
        assignment_id: UUID,
        student_id: UUID
    ) -> Optional[AssignmentSubmission]:
        """
        Get a student's submission for an assignment.
        
        Args:
            assignment_id: Assignment UUID
            student_id: Student UUID
            
        Returns:
            Submission instance or None
        """
        query = select(AssignmentSubmission).where(
            and_(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.student_id == student_id
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def count_submissions(self, assignment_id: UUID) -> int:
        """
        Count total submissions for an assignment.
        
        Args:
            assignment_id: Assignment UUID
            
        Returns:
            Number of submissions
        """
        count_query = select(func.count(AssignmentSubmission.id)).where(
            AssignmentSubmission.assignment_id == assignment_id
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    async def count_graded_submissions(self, assignment_id: UUID) -> int:
        """
        Count graded submissions for an assignment.
        
        Args:
            assignment_id: Assignment UUID
            
        Returns:
            Number of graded submissions
        """
        count_query = select(func.count(AssignmentSubmission.id)).where(
            and_(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.graded_at.is_not(None)
            )
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    async def get_ungraded_submissions(
        self,
        assignment_id: UUID
    ) -> List[AssignmentSubmission]:
        """
        Get all ungraded submissions for an assignment.
        
        Args:
            assignment_id: Assignment UUID
            
        Returns:
            List of ungraded submissions
        """
        query = select(AssignmentSubmission).where(
            and_(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.graded_at.is_(None)
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_late_submissions(
        self,
        assignment_id: UUID
    ) -> List[AssignmentSubmission]:
        """
        Get all late submissions for an assignment.
        
        Args:
            assignment_id: Assignment UUID
            
        Returns:
            List of late submissions
        """
        # Get assignment to check due date
        assignment = await self.get_by_id(assignment_id)
        if not assignment:
            return []
        
        query = select(AssignmentSubmission).where(
            and_(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.submitted_at > assignment.due_date
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== STATISTICS ====================
    async def get_assignment_statistics(self, assignment_id: UUID) -> dict:
        """
        Get statistics for an assignment.
        
        Args:
            assignment_id: Assignment UUID
            
        Returns:
            Dictionary with statistics
        """
        assignment = await self.get_by_id(assignment_id)
        if not assignment:
            return {}
        
        total_students = assignment.class_id  # This would need actual class count
        submissions, _ = await self.get_submissions(assignment_id, skip=0, limit=9999)
        graded = [s for s in submissions if s.graded_at]
        
        return {
            "total_assigned": total_students,
            "total_submitted": len(submissions),
            "total_graded": len(graded),
            "late_submissions": len(await self.get_late_submissions(assignment_id)),
            "not_submitted": total_students - len(submissions),
            "submission_rate": (len(submissions) / total_students * 100) if total_students else 0,
            "grades": [s.marks for s in graded] if graded else []
        }
