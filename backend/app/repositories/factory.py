"""
Repository Factory - Central dependency injection for all repositories
"""

from sqlalchemy.ext.asyncio import AsyncSession
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


class RepositoryFactory:
    """
    Factory that creates and manages all repository instances.
    Allows lazy initialization of repositories and provides dependency injection.
    
    Usage in FastAPI endpoints:
        @app.get("/students")
        async def get_students(
            repos: RepositoryFactory = Depends(get_repos)
        ):
            students, total = await repos.student.list()
            return students
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        
        # Cache for lazy-loaded repositories
        self._user_repo = None
        self._student_repo = None
        self._staff_repo = None
        self._admin_hod_repo = None
        self._session_year_repo = None
        self._department_repo = None
        self._class_repo = None
        self._subject_repo = None
        self._timetable_repo = None
        self._quiz_repo = None
        self._assignment_repo = None
        self._attendance_repo = None
        self._student_leave_repo = None
        self._staff_leave_repo = None
        self._feedback_repo = None
        self._message_repo = None
        self._announcement_repo = None
        self._notification_repo = None
        self._notification_preferences_repo = None
        self._reminder_repo = None
    
    # ==================== AUTHENTICATION ====================
    @property
    def user(self) -> UserRepository:
        """User repository"""
        if self._user_repo is None:
            self._user_repo = UserRepository(self.db_session)
        return self._user_repo
    
    # ==================== STUDENT ====================
    @property
    def student(self) -> StudentRepository:
        """Student repository"""
        if self._student_repo is None:
            self._student_repo = StudentRepository(self.db_session)
        return self._student_repo
    
    # ==================== STAFF ====================
    @property
    def staff(self) -> StaffRepository:
        """Staff repository"""
        if self._staff_repo is None:
            self._staff_repo = StaffRepository(self.db_session)
        return self._staff_repo
    
    @property
    def admin_hod(self) -> AdminHODRepository:
        """Admin/HOD repository"""
        if self._admin_hod_repo is None:
            self._admin_hod_repo = AdminHODRepository(self.db_session)
        return self._admin_hod_repo
    
    # ==================== ACADEMIC STRUCTURE ====================
    @property
    def session_year(self) -> SessionYearRepository:
        """Session year repository"""
        if self._session_year_repo is None:
            self._session_year_repo = SessionYearRepository(self.db_session)
        return self._session_year_repo
    
    @property
    def department(self) -> DepartmentRepository:
        """Department repository"""
        if self._department_repo is None:
            self._department_repo = DepartmentRepository(self.db_session)
        return self._department_repo
    
    @property
    def class_repo(self) -> ClassRepository:
        """Class repository"""
        if self._class_repo is None:
            self._class_repo = ClassRepository(self.db_session)
        return self._class_repo
    
    @property
    def subject(self) -> SubjectRepository:
        """Subject repository"""
        if self._subject_repo is None:
            self._subject_repo = SubjectRepository(self.db_session)
        return self._subject_repo
    
    @property
    def timetable(self) -> TimeTableRepository:
        """TimeTable repository"""
        if self._timetable_repo is None:
            self._timetable_repo = TimeTableRepository(self.db_session)
        return self._timetable_repo
    
    # ==================== ASSESSMENT ====================
    @property
    def quiz(self) -> QuizRepository:
        """Quiz repository"""
        if self._quiz_repo is None:
            self._quiz_repo = QuizRepository(self.db_session)
        return self._quiz_repo
    
    # ==================== ASSIGNMENT ====================
    @property
    def assignment(self) -> AssignmentRepository:
        """Assignment repository"""
        if self._assignment_repo is None:
            self._assignment_repo = AssignmentRepository(self.db_session)
        return self._assignment_repo
    
    # ==================== ATTENDANCE ====================
    @property
    def attendance(self) -> AttendanceRepository:
        """Attendance repository"""
        if self._attendance_repo is None:
            self._attendance_repo = AttendanceRepository(self.db_session)
        return self._attendance_repo
    
    # ==================== LEAVE ====================
    @property
    def student_leave(self) -> StudentLeaveRepository:
        """Student leave repository"""
        if self._student_leave_repo is None:
            self._student_leave_repo = StudentLeaveRepository(self.db_session)
        return self._student_leave_repo
    
    @property
    def staff_leave(self) -> StaffLeaveRepository:
        """Staff leave repository"""
        if self._staff_leave_repo is None:
            self._staff_leave_repo = StaffLeaveRepository(self.db_session)
        return self._staff_leave_repo
    
    # ==================== FEEDBACK & MESSAGING ====================
    @property
    def feedback(self) -> FeedbackRepository:
        """Feedback repository"""
        if self._feedback_repo is None:
            self._feedback_repo = FeedbackRepository(self.db_session)
        return self._feedback_repo
    
    @property
    def message(self) -> MessageRepository:
        """Message repository"""
        if self._message_repo is None:
            self._message_repo = MessageRepository(self.db_session)
        return self._message_repo
    
    @property
    def announcement(self) -> AnnouncementRepository:
        """Announcement repository"""
        if self._announcement_repo is None:
            self._announcement_repo = AnnouncementRepository(self.db_session)
        return self._announcement_repo
    
    # ==================== NOTIFICATIONS ====================
    @property
    def notification(self) -> NotificationRepository:
        """Notification repository"""
        if self._notification_repo is None:
            self._notification_repo = NotificationRepository(self.db_session)
        return self._notification_repo
    
    @property
    def notification_preferences(self) -> NotificationPreferencesRepository:
        """Notification preferences repository"""
        if self._notification_preferences_repo is None:
            self._notification_preferences_repo = NotificationPreferencesRepository(
                self.db_session
            )
        return self._notification_preferences_repo
    
    @property
    def reminder(self) -> ReminderRepository:
        """Reminder repository"""
        if self._reminder_repo is None:
            self._reminder_repo = ReminderRepository(self.db_session)
        return self._reminder_repo
    
    # ==================== TRANSACTION CONTROL ====================
    async def commit(self) -> None:
        """Commit all pending changes"""
        await self.db_session.commit()
    
    async def rollback(self) -> None:
        """Rollback all pending changes"""
        await self.db_session.rollback()
    
    async def flush(self) -> None:
        """Flush pending changes without commit"""
        await self.db_session.flush()
