"""
Services Layer - Business logic and orchestration.

Provides service classes for all domain operations:
- AuthService - User registration, login, token management
- UserService - Profile management, role checking
- StudentService - Enrollment, transfers, grades
- QuizService - Question management, auto-grading
- And more...

Each service inherits from BaseService and uses repositories for data access.

Usage:
    from fastapi import Depends
    from app.services import get_services, ServiceFactory
    
    @app.post("/login")
    async def login(
        credentials: LoginRequest,
        services: ServiceFactory = Depends(get_services)
    ):
        result = await services.auth.login_user(
            email=credentials.email,
            password=credentials.password
        )
        return result
"""

from typing import TYPE_CHECKING

from fastapi import Depends

from app.repositories import RepositoryFactory, get_repos
from app.services.base import BaseService
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.student_service import StudentService
from app.services.quiz_service import QuizService
from app.services.assessment_service import AssessmentService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ServiceFactory:
    """
    Factory for dependency injection of all service classes.
    
    Provides lazy-loaded access to services with shared repository access.
    Each service uses the same RepositoryFactory instance for transaction consistency.
    
    Usage:
        services = ServiceFactory(repos)
        await services.auth.login_user(email, password)
        await services.user.get_user_profile(user_id)
        await services.quiz.create_quiz(quiz_data)
    
    Attributes:
        auth: AuthService for authentication operations
        user: UserService for profile management
        student: StudentService for enrollment operations
        quiz: QuizService for assessment management
        assignment: AssignmentService for assignment operations
        attendance: AttendanceService for attendance tracking
    """

    def __init__(self, repos: RepositoryFactory) -> None:
        """
        Initialize service factory with repositories.
        
        Args:
            repos: RepositoryFactory instance for data access
        """
        self.repos = repos
        self._auth_service: AuthService | None = None
        self._user_service: UserService | None = None
        self._student_service: StudentService | None = None
        self._quiz_service: QuizService | None = None
        self._assessment_service: AssessmentService | None = None
        # Future services will be lazily loaded similarly

    @property
    def auth(self) -> AuthService:
        """
        Get AuthService instance (lazy-loaded).
        
        Returns:
            AuthService instance for authentication operations
        """
        if self._auth_service is None:
            self._auth_service = AuthService(self.repos)
        return self._auth_service

    @property
    def user(self) -> UserService:
        """
        Get UserService instance (lazy-loaded).
        
        Returns:
            UserService instance for profile management operations
        """
        if self._user_service is None:
            self._user_service = UserService(self.repos)
        return self._user_service

    @property
    def student(self) -> StudentService:
        """
        Get StudentService instance (lazy-loaded).
        
        Returns:
            StudentService instance for enrollment and academic operations
        """
        if self._student_service is None:
            self._student_service = StudentService(self.repos)
        return self._student_service

    @property
    def quiz(self) -> QuizService:
        """
        Get QuizService instance (lazy-loaded).
        
        Returns:
            QuizService instance for quiz management and grading operations
        """
        if self._quiz_service is None:
            self._quiz_service = QuizService(self.repos)
        return self._quiz_service

    @property
    def assessment(self) -> AssessmentService:
        """
        Get AssessmentService instance (lazy-loaded).
        
        Returns:
            AssessmentService instance for grading and assessment operations
        """
        if self._assessment_service is None:
            self._assessment_service = AssessmentService(self.repos)
        return self._assessment_service

    # TODO: Add other service properties as they're created


async def get_services(repos: RepositoryFactory = Depends(get_repos)) -> ServiceFactory:
    """
    Dependency injection function for FastAPI endpoints.
    
    Provides ServiceFactory instance with all services properly initialized.
    
    Usage:
        @app.post("/login")
        async def login(
            credentials: LoginRequest,
            services: ServiceFactory = Depends(get_services)
        ):
            result = await services.auth.login_user(
                email=credentials.email,
                password=credentials.password
            )
            return result
    
    Args:
        repos: RepositoryFactory from get_repos dependency
    
    Returns:
        ServiceFactory instance with lazy-loaded services
    """
    return ServiceFactory(repos)


__all__ = [
    # Base
    "BaseService",
    
    # Services
    "AuthService",
    "UserService",
    "StudentService",
    "QuizService",
    "AssessmentService",
    # And more...
    
    # Factory & DI
    "ServiceFactory",
    "get_services",
]
