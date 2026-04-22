"""ORM model registry — import all models here so Base.metadata is fully populated."""

from app.models.base import BaseModel  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.academic import (  # noqa: F401
    Department,
    SessionYear,
    ClassRoom,
    Subject,
)
from app.models.student import StudentProfile  # noqa: F401
from app.models.staff import StaffProfile  # noqa: F401
from app.models.assessment import (  # noqa: F401
    Quiz,
    Question,
    QuizAttempt,
    QuizResult,
    QuizStatus,
    QuestionType,
    AttemptStatus,
)
from app.models.assignment import (  # noqa: F401
    Assignment,
    AssignmentSubmission,
    AssignmentStatus,
    SubmissionStatus,
)
from app.models.attendance import (  # noqa: F401
    AttendanceSession,
    AttendanceRecord,
    AttendanceStatus,
)
from app.models.feedback import FeedbackStaff, FeedbackStudent  # noqa: F401
from app.models.leave import LeaveRequest, LeaveType, LeaveStatus  # noqa: F401
from app.models.notification import Notification, NotificationType  # noqa: F401
from app.models.audit import AuditLog, AuditAction  # noqa: F401
