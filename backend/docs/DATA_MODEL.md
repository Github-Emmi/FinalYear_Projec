# Data Model: School Management System

All entities use UUID v4 primary keys, `created_at`, `updated_at` timestamps,
and `is_deleted` soft-delete flag (inherited from `BaseModel` in `app/models/base.py`).

## Entity Overview (Phase 2 implementation targets)

| Model file | Entity | Key relationships |
|------------|--------|-------------------|
| `user.py` | User | FK → Department, Role |
| `student.py` | StudentProfile | FK → User, ClassRoom, SessionYear |
| `staff.py` | StaffProfile | FK → User, Department |
| `academic.py` | Department | standalone |
| `academic.py` | ClassRoom | FK → Department |
| `academic.py` | Subject | FK → ClassRoom, StaffProfile |
| `academic.py` | SessionYear | standalone |
| `assessment.py` | Quiz | FK → Subject, StaffProfile |
| `assessment.py` | Question | FK → Quiz |
| `assessment.py` | QuizAttempt | FK → Quiz, StudentProfile |
| `assessment_results.py` | QuizResult | FK → QuizAttempt, Question |
| `assignment.py` | Assignment | FK → Subject, StaffProfile |
| `assignment.py` | AssignmentSubmission | FK → Assignment, StudentProfile |
| `attendance.py` | AttendanceSession | FK → ClassRoom, Subject, StaffProfile |
| `attendance.py` | AttendanceRecord | FK → AttendanceSession, StudentProfile |
| `feedback.py` | FeedbackStaff | FK → StaffProfile, StudentProfile |
| `feedback.py` | FeedbackStudent | FK → StudentProfile, StaffProfile |
| `leave.py` | LeaveRequest | FK → User |
| `notification.py` | Notification | FK → User (sender), User (recipient) |
| `audit.py` | AuditLog | FK → User |

## Field Conventions

- `id`: `UUID(as_uuid=True)`, PK, `default=uuid.uuid4`, not nullable
- `created_at`: `DateTime`, server_default `func.now()`, not nullable, indexed
- `updated_at`: `DateTime`, server_default `func.now()`, `onupdate=func.now()`, not nullable
- `is_deleted`: `Boolean`, default `False`, not nullable — never hard delete rows
- Foreign keys: `UUID(as_uuid=True)`, `ForeignKey("tablename.id")`, nullable where optional
- String fields: `String(255)` for names/labels, `Text` for long-form content
- Enum fields: Python `enum.Enum` mapped to `String(50)` column (not DB ENUM type — easier migration)

## Soft Delete Convention

Repositories MUST filter `WHERE is_deleted = FALSE` on all read queries.
A dedicated `delete()` method on the base repository sets `is_deleted = True`
and `updated_at = now()` rather than issuing a SQL DELETE.
