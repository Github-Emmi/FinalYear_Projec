"""
Quiz Repository - Assessment and quiz queries
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.models.assessment import Quiz, Question, StudentQuizSubmission
from app.repositories.base import BaseRepository


class QuizRepository(BaseRepository[Quiz]):
    """
    Specialized repository for Quiz-specific operations.
    Handles published quizzes, questions loading, and submission tracking.
    """
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, Quiz)
    
    # ==================== STATUS QUERIES ====================
    async def get_published_quizzes(self, class_id: UUID) -> List[Quiz]:
        """
        Get only published quizzes for a class.
        
        Args:
            class_id: Class UUID
            
        Returns:
            List of published quizzes
        """
        query = select(Quiz).where(
            and_(
                Quiz.class_id == class_id,
                Quiz.status == "PUBLISHED",
                Quiz.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_draft_quizzes(self, staff_id: UUID) -> List[Quiz]:
        """
        Get draft quizzes for a staff member.
        
        Args:
            staff_id: Staff UUID
            
        Returns:
            List of draft quizzes
        """
        query = select(Quiz).where(
            and_(
                Quiz.staff_id == staff_id,
                Quiz.status == "DRAFT",
                Quiz.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== EAGER LOADING ====================
    async def get_quiz_with_questions(self, quiz_id: UUID) -> Optional[Quiz]:
        """
        Get quiz with all its questions eagerly loaded.
        
        Args:
            quiz_id: Quiz UUID
            
        Returns:
            Quiz instance with questions loaded
            
        Example:
            quiz = await quiz_repo.get_quiz_with_questions(uuid)
            for question in quiz.questions:
                print(question.question_text)
        """
        query = select(Quiz).where(
            Quiz.id == quiz_id
        ).options(selectinload(Quiz.questions))
        
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    # ==================== TIME-BASED QUERIES ====================
    async def get_active_quizzes(self, class_id: UUID) -> List[Quiz]:
        """
        Get currently active quizzes (within start_time and end_time).
        
        Args:
            class_id: Class UUID
            
        Returns:
            List of active quizzes
        """
        now = datetime.utcnow()
        query = select(Quiz).where(
            and_(
                Quiz.class_id == class_id,
                Quiz.start_time <= now,
                Quiz.end_time >= now,
                Quiz.status == "PUBLISHED",
                Quiz.is_deleted == False
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_upcoming_quizzes(self, class_id: UUID) -> List[Quiz]:
        """
        Get quizzes that haven't started yet.
        
        Args:
            class_id: Class UUID
            
        Returns:
            List of upcoming quizzes
        """
        now = datetime.utcnow()
        query = select(Quiz).where(
            and_(
                Quiz.class_id == class_id,
                Quiz.start_time > now,
                Quiz.status == "PUBLISHED",
                Quiz.is_deleted == False
            )
        ).order_by(Quiz.start_time.asc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_past_quizzes(self, class_id: UUID) -> List[Quiz]:
        """
        Get quizzes that have ended.
        
        Args:
            class_id: Class UUID
            
        Returns:
            List of past quizzes
        """
        now = datetime.utcnow()
        query = select(Quiz).where(
            and_(
                Quiz.class_id == class_id,
                Quiz.end_time < now,
                Quiz.is_deleted == False
            )
        ).order_by(Quiz.end_time.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    # ==================== SUBMISSION QUERIES ====================
    async def get_student_submissions(
        self,
        quiz_id: UUID
    ) -> List[StudentQuizSubmission]:
        """
        Get all student submissions for a quiz.
        
        Args:
            quiz_id: Quiz UUID
            
        Returns:
            List of submissions
        """
        query = select(StudentQuizSubmission).where(
            StudentQuizSubmission.quiz_id == quiz_id
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def get_student_quiz_submission(
        self,
        quiz_id: UUID,
        student_id: UUID
    ) -> Optional[StudentQuizSubmission]:
        """
        Get a specific student's submission for a quiz.
        
        Args:
            quiz_id: Quiz UUID
            student_id: Student UUID
            
        Returns:
            Submission instance or None
        """
        query = select(StudentQuizSubmission).where(
            and_(
                StudentQuizSubmission.quiz_id == quiz_id,
                StudentQuizSubmission.student_id == student_id
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def count_submissions(self, quiz_id: UUID) -> int:
        """
        Count total submissions for a quiz.
        
        Args:
            quiz_id: Quiz UUID
            
        Returns:
            Number of submissions
        """
        count_query = select(func.count(StudentQuizSubmission.id)).where(
            StudentQuizSubmission.quiz_id == quiz_id
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    async def count_graded_submissions(self, quiz_id: UUID) -> int:
        """Count graded submissions for a quiz."""
        count_query = select(func.count(StudentQuizSubmission.id)).where(
            and_(
                StudentQuizSubmission.quiz_id == quiz_id,
                StudentQuizSubmission.is_graded == True
            )
        )
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    # ==================== STATISTICS ====================
    async def get_quiz_statistics(self, quiz_id: UUID) -> dict:
        """
        Get statistics for a quiz (avg score, pass rate, etc).
        
        Args:
            quiz_id: Quiz UUID
            
        Returns:
            Dictionary with statistics
        """
        submissions = await self.get_student_submissions(quiz_id)
        
        if not submissions:
            return {
                "total_submissions": 0,
                "graded_submissions": 0,
                "average_score": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0,
                "pass_rate": 0.0
            }
        
        graded = [s for s in submissions if s.is_graded]
        if not graded:
            return {
                "total_submissions": len(submissions),
                "graded_submissions": 0,
                "average_score": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0,
                "pass_rate": 0.0
            }
        
        scores = [s.total_score for s in graded]
        passed = len([s for s in graded if s.percentage >= 50])
        
        return {
            "total_submissions": len(submissions),
            "graded_submissions": len(graded),
            "average_score": sum(scores) / len(scores),
            "highest_score": max(scores),
            "lowest_score": min(scores),
            "pass_rate": (passed / len(graded)) * 100 if graded else 0.0
        }
