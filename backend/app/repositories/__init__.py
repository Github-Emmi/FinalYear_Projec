"""
Repositories - Data access layer with Repository Pattern
Provides generic and specific repositories for all entities with lazy initialization.
"""

# Base repository
from app.repositories.base import BaseRepository

# Specific repositories
from app.repositories.user import UserRepository
from app.repositories.student import StudentRepository
from app.repositories.staff import StaffRepository, AdminHODRepository
from app.repositories.academic import (
    SessionYearRepository,
    DepartmentRepository,
    ClassRepository,
    SubjectRepository,
    TimeTableRepository
)
from app.repositories.quiz import QuizRepository
from app.repositories.assignment import AssignmentRepository
from app.repositories.attendance import AttendanceRepository
from app.repositories.leave import StudentLeaveRepository, StaffLeaveRepository
from app.repositories.feedback import FeedbackRepository, MessageRepository, AnnouncementRepository
from app.repositories.notification import (
    NotificationRepository,
    NotificationPreferencesRepository,
    ReminderRepository
)

# Factory
from app.repositories.factory import RepositoryFactory

# Dependency injection
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session


async def get_repos(db_session: AsyncSession = Depends(lambda: async_session())) -> RepositoryFactory:
    """
    Dependency injection function for FastAPI endpoints.
    
    Usage:
        @app.get("/students")
        async def get_students(repos: RepositoryFactory = Depends(get_repos)):
            students, total = await repos.student.list()
            return students
    """
    return RepositoryFactory(db_session)


__all__ = [
    # Base
    "BaseRepository",
    
    # User & Authentication
    "UserRepository",
    
    # Student
    "StudentRepository",
    
    # Staff & Admin
    "StaffRepository",
    "AdminHODRepository",
    
    # Academic Structure
    "SessionYearRepository",
    "DepartmentRepository",
    "ClassRepository",
    "SubjectRepository",
    "TimeTableRepository",
    
    # Assessment
    "QuizRepository",
    
    # Assignment
    "AssignmentRepository",
    
    # Attendance
    "AttendanceRepository",
    
    # Leave
    "StudentLeaveRepository",
    "StaffLeaveRepository",
    
    # Feedback & Messaging
    "FeedbackRepository",
    "MessageRepository",
    "AnnouncementRepository",
    
    # Notifications
    "NotificationRepository",
    "NotificationPreferencesRepository",
    "ReminderRepository",
    
    # Factory & DI
    "RepositoryFactory",
    "get_repos",
]
