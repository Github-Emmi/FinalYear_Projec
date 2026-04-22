"""Repository registry."""

from app.repositories.base import BaseRepository  # noqa: F401
from app.repositories.user import UserRepository  # noqa: F401
from app.repositories.student import StudentRepository  # noqa: F401
from app.repositories.staff import StaffRepository  # noqa: F401
from app.repositories.academic import (  # noqa: F401
    DepartmentRepository,
    SessionYearRepository,
    ClassRoomRepository,
    SubjectRepository,
)
from app.repositories.assessment import (  # noqa: F401
    QuizRepository,
    QuestionRepository,
    QuizAttemptRepository,
    QuizResultRepository,
)
from app.repositories.assignment import (  # noqa: F401
    AssignmentRepository,
    SubmissionRepository,
)
from app.repositories.attendance import (  # noqa: F401
    AttendanceSessionRepository,
    AttendanceRecordRepository,
)
from app.repositories.feedback import (  # noqa: F401
    FeedbackStaffRepository,
    FeedbackStudentRepository,
)
from app.repositories.leave import LeaveRepository  # noqa: F401
from app.repositories.notification import NotificationRepository  # noqa: F401
from app.repositories.audit import AuditRepository  # noqa: F401
from app.repositories.factory import RepositoryFactory  # noqa: F401
