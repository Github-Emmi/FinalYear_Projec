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
from app.services.assignment_service import AssignmentService
from app.services.leave_service import LeaveService
from app.services.attendance_service import AttendanceService
from app.services.notification_service import NotificationService
from app.services.analytics_service import AnalyticsService
from app.services.staff_service import StaffService
from app.services.academic_service import AcademicService
from app.services.subject_service import SubjectService
from app.services.feedback_service import FeedbackService
from app.services.report_service import ReportService
from app.services.file_service import FileService
from app.services.email_service import EmailService

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
        leave: LeaveService for leave request management
        assessment: AssessmentService for grading operations
        attendance: AttendanceService for attendance tracking operations
        notification: NotificationService for notification management operations
        analytics: AnalyticsService for analytics and reporting operations
        staff: StaffService for staff management operations
        academic: AcademicService for academic structure and timetable operations
        subject: SubjectService for subject management and schedule operations
        feedback: FeedbackService for messaging, announcements, and feedback operations
        report: ReportService for transcripts, analytics, and report generation operations
        file: FileService for cloud storage and file management operations (Cloudinary/S3)
        email: EmailService for Zoho Mail SMTP integration and email communications
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
        self._assignment_service: AssignmentService | None = None
        self._leave_service: LeaveService | None = None
        self._attendance_service: AttendanceService | None = None
        self._notification_service: NotificationService | None = None
        self._analytics_service: AnalyticsService | None = None
        self._staff_service: StaffService | None = None
        self._academic_service: AcademicService | None = None
        self._subject_service: SubjectService | None = None
        self._feedback_service: FeedbackService | None = None
        self._report_service: ReportService | None = None
        self._file_service: FileService | None = None
        self._email_service: EmailService | None = None

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

    @property
    def assignment(self) -> AssignmentService:
        """
        Get AssignmentService instance (lazy-loaded).
        
        Returns:
            AssignmentService instance for assignment management operations
        """
        if self._assignment_service is None:
            self._assignment_service = AssignmentService(self.repos)
        return self._assignment_service

    @property
    def leave(self) -> LeaveService:
        """
        Get LeaveService instance (lazy-loaded).
        
        Returns:
            LeaveService instance for leave request and approval operations
        """
        if self._leave_service is None:
            self._leave_service = LeaveService(self.repos)
        return self._leave_service

    @property
    def attendance(self) -> AttendanceService:
        """
        Get AttendanceService instance (lazy-loaded).
        
        Returns:
            AttendanceService instance for attendance tracking and reporting operations
        """
        if self._attendance_service is None:
            self._attendance_service = AttendanceService(self.repos.session, self.repos)
        return self._attendance_service

    @property
    def notification(self) -> NotificationService:
        """
        Get NotificationService instance (lazy-loaded).
        
        Returns:
            NotificationService instance for notification management and delivery operations
        """
        if self._notification_service is None:
            self._notification_service = NotificationService(self.repos.session, self.repos)
        return self._notification_service

    @property
    def analytics(self) -> AnalyticsService:
        """
        Get AnalyticsService instance (lazy-loaded).
        
        Returns:
            AnalyticsService instance for analytics, reporting, and performance prediction operations
        """
        if self._analytics_service is None:
            self._analytics_service = AnalyticsService(self.repos.session, self.repos)
        return self._analytics_service

    @property
    def staff(self) -> StaffService:
        """
        Get StaffService instance (lazy-loaded).
        
        Returns:
            StaffService instance for staff management, assignments, and leave processing operations
        """
        if self._staff_service is None:
            self._staff_service = StaffService(self.repos.session, self.repos)
        return self._staff_service

    @property
    def academic(self) -> AcademicService:
        """
        Get AcademicService instance (lazy-loaded).
        
        Returns:
            AcademicService instance for academic structure, sessions, and timetable operations
        """
        if self._academic_service is None:
            self._academic_service = AcademicService(self.repos.session, self.repos)
        return self._academic_service

    @property
    def subject(self) -> SubjectService:
        """
        Get SubjectService instance (lazy-loaded).
        
        Returns:
            SubjectService instance for subject management, qualifications, and schedule conflict resolution operations
        """
        if self._subject_service is None:
            self._subject_service = SubjectService(self.repos)
        return self._subject_service

    @property
    def feedback(self) -> FeedbackService:
        """
        Get FeedbackService instance (lazy-loaded).
        
        Returns:
            FeedbackService instance for messaging, announcements, support tickets, and feedback operations
        """
        if self._feedback_service is None:
            self._feedback_service = FeedbackService(self.repos)
        return self._feedback_service

    @property
    def report(self) -> ReportService:
        """
        Get ReportService instance (lazy-loaded).
        
        Returns:
            ReportService instance for report generation, transcripts, and analytics operations
        """
        if self._report_service is None:
            self._report_service = ReportService(self.repos)
        return self._report_service

    @property
    def file(self) -> FileService:
        """
        Get FileService instance (lazy-loaded).
        
        Returns:
            FileService instance for cloud storage, file uploads, and Cloudinary/S3 operations
        """
        if self._file_service is None:
            self._file_service = FileService(self.repos)
        return self._file_service

    @property
    def email(self) -> EmailService:
        """
        Get EmailService instance (lazy-loaded).
        
        Returns:
            EmailService instance for Zoho Mail SMTP transactional and bulk email operations
        """
        if self._email_service is None:
            self._email_service = EmailService(self.repos)
        return self._email_service


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
    "AssignmentService",
    "LeaveService",
    "AttendanceService",
    "NotificationService",
    "AnalyticsService",
    "StaffService",
    "AcademicService",
    "SubjectService",
    "FeedbackService",
    "ReportService",
    "FileService",
    "EmailService",
    # And more...
    
    # Factory & DI
    "ServiceFactory",
    "get_services",
]
