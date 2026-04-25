"""RepositoryFactory — single entry point to create any repository.

Usage in a FastAPI dependency::

    from app.repositories.factory import RepositoryFactory
    from app.core.database import get_db

    async def get_repo_factory(db: AsyncSession = Depends(get_db)):
        return RepositoryFactory(db)
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.academic import (
    ClassRoomRepository,
    DepartmentRepository,
    SessionYearRepository,
    SubjectRepository,
)
from app.repositories.assessment import (
    QuestionRepository,
    QuizAttemptRepository,
    QuizRepository,
    QuizResultRepository,
)
from app.repositories.assignment import AssignmentRepository, SubmissionRepository
from app.repositories.attendance import (
    AttendanceRecordRepository,
    AttendanceSessionRepository,
)
from app.repositories.audit import AuditRepository
from app.repositories.feedback import FeedbackStaffRepository, FeedbackStudentRepository
from app.repositories.leave import LeaveRepository
from app.repositories.notification import NotificationRepository
from app.repositories.staff import StaffRepository
from app.repositories.student import StudentRepository
from app.repositories.user import UserRepository


class RepositoryFactory:
    """Instantiate any repository bound to the current session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Core ───────────────────────────────────────────────────────────────────
    @property
    def users(self) -> UserRepository:
        return UserRepository(self._session)

    @property
    def students(self) -> StudentRepository:
        return StudentRepository(self._session)

    @property
    def staff(self) -> StaffRepository:
        return StaffRepository(self._session)

    # ── Academic ───────────────────────────────────────────────────────────────
    @property
    def departments(self) -> DepartmentRepository:
        return DepartmentRepository(self._session)

    @property
    def session_years(self) -> SessionYearRepository:
        return SessionYearRepository(self._session)

    @property
    def classrooms(self) -> ClassRoomRepository:
        return ClassRoomRepository(self._session)

    @property
    def subjects(self) -> SubjectRepository:
        return SubjectRepository(self._session)

    # ── Assessment ─────────────────────────────────────────────────────────────
    @property
    def quizzes(self) -> QuizRepository:
        return QuizRepository(self._session)

    @property
    def questions(self) -> QuestionRepository:
        return QuestionRepository(self._session)

    @property
    def quiz_attempts(self) -> QuizAttemptRepository:
        return QuizAttemptRepository(self._session)

    @property
    def quiz_results(self) -> QuizResultRepository:
        return QuizResultRepository(self._session)

    # ── Assignment ─────────────────────────────────────────────────────────────
    @property
    def assignments(self) -> AssignmentRepository:
        return AssignmentRepository(self._session)

    @property
    def submissions(self) -> SubmissionRepository:
        return SubmissionRepository(self._session)

    # ── Attendance ─────────────────────────────────────────────────────────────
    @property
    def attendance_sessions(self) -> AttendanceSessionRepository:
        return AttendanceSessionRepository(self._session)

    @property
    def attendance_records(self) -> AttendanceRecordRepository:
        return AttendanceRecordRepository(self._session)

    # ── Feedback ───────────────────────────────────────────────────────────────
    @property
    def feedback_staff(self) -> FeedbackStaffRepository:
        return FeedbackStaffRepository(self._session)

    @property
    def feedback_students(self) -> FeedbackStudentRepository:
        return FeedbackStudentRepository(self._session)

    # ── Leave ──────────────────────────────────────────────────────────────────
    @property
    def leaves(self) -> LeaveRepository:
        return LeaveRepository(self._session)

    # ── Notification ───────────────────────────────────────────────────────────
    @property
    def notifications(self) -> NotificationRepository:
        return NotificationRepository(self._session)

    # ── Audit ──────────────────────────────────────────────────────────────────
    @property
    def audit(self) -> AuditRepository:
        return AuditRepository(self._session)
