"""Pydantic schema registry."""

from app.schemas.base import BaseResponse  # noqa: F401
from app.schemas.auth import (  # noqa: F401
    LoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    PasswordChangeRequest,
)
from app.schemas.user import UserCreate, UserUpdate, UserResponse  # noqa: F401
from app.schemas.academic import (  # noqa: F401
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    SessionYearCreate, SessionYearUpdate, SessionYearResponse,
    ClassRoomCreate, ClassRoomUpdate, ClassRoomResponse,
    SubjectCreate, SubjectUpdate, SubjectResponse,
)
from app.schemas.student import (  # noqa: F401
    StudentProfileCreate, StudentProfileUpdate, StudentProfileResponse,
)
from app.schemas.staff import (  # noqa: F401
    StaffProfileCreate, StaffProfileUpdate, StaffProfileResponse,
)
from app.schemas.assessment import (  # noqa: F401
    QuizCreate, QuizUpdate, QuizResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse,
    QuizAttemptCreate, QuizAttemptUpdate, QuizAttemptResponse,
    QuizResultCreate, QuizResultResponse,
)
from app.schemas.assignment import (  # noqa: F401
    AssignmentCreate, AssignmentUpdate, AssignmentResponse,
    SubmissionCreate, SubmissionUpdate, SubmissionResponse,
)
from app.schemas.attendance import (  # noqa: F401
    AttendanceSessionCreate, AttendanceSessionUpdate, AttendanceSessionResponse,
    AttendanceRecordCreate, AttendanceRecordUpdate, AttendanceRecordResponse,
)
from app.schemas.feedback import (  # noqa: F401
    FeedbackStaffCreate, FeedbackStaffUpdate, FeedbackStaffResponse,
    FeedbackStudentCreate, FeedbackStudentUpdate, FeedbackStudentResponse,
)
from app.schemas.leave import (  # noqa: F401
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestReview, LeaveRequestResponse,
)
from app.schemas.notification import (  # noqa: F401
    NotificationCreate, NotificationUpdate, NotificationResponse,
)
