"""Service layer registry."""

from app.services.auth_service import AuthService  # noqa: F401
from app.services.user_service import UserService  # noqa: F401
from app.services.student_service import StudentService  # noqa: F401
from app.services.staff_service import StaffService  # noqa: F401
from app.services.assessment_service import AssessmentService  # noqa: F401
from app.services.assignment_service import AssignmentService  # noqa: F401
from app.services.attendance_service import AttendanceService  # noqa: F401
from app.services.leave_service import LeaveService  # noqa: F401
from app.services.notification_service import NotificationService  # noqa: F401
from app.services.analytics_service import AnalyticsService  # noqa: F401
from app.services.email_service import EmailService  # noqa: F401
from app.services.academic_service import AcademicService  # noqa: F401
