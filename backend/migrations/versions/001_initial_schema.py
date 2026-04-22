"""001 initial schema — 20 tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=150), nullable=False),
        sa.Column("last_name", sa.String(length=150), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    # 2. departments
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 3. session_years
    op.create_table(
        "session_years",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. staff_profiles (→ users, departments)
    op.create_table(
        "staff_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("designation", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("profile_picture", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # 5. classrooms (→ departments)
    op.create_table(
        "classrooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. student_profiles (→ users, classrooms, session_years)
    op.create_table(
        "student_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_year_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("roll_number", sa.String(length=50), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("profile_picture", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_year_id"], ["session_years.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # 7. subjects (→ classrooms, staff_profiles)
    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. quizzes (→ subjects, staff_profiles)
    op.create_table(
        "quizzes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pass_score", sa.Float(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_grading_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9. assignments (→ subjects, staff_profiles)
    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="100"),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("ai_grading_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 10. questions (→ quizzes)
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False),
        sa.Column("option_a", sa.Text(), nullable=True),
        sa.Column("option_b", sa.Text(), nullable=True),
        sa.Column("option_c", sa.Text(), nullable=True),
        sa.Column("option_d", sa.Text(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("marks", sa.Float(), nullable=False, server_default="1"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 11. quiz_attempts (→ quizzes, student_profiles)
    op.create_table(
        "quiz_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="in_progress"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 12. quiz_results (→ quiz_attempts, questions)
    op.create_table(
        "quiz_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("marks_earned", sa.Float(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["quiz_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 13. assignment_submissions (→ assignments, student_profiles)
    op.create_table(
        "assignment_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="submitted"),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 14. attendance_sessions (→ classrooms, subjects, staff_profiles)
    op.create_table(
        "attendance_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attendance_sessions_date", "attendance_sessions", ["date"])

    # 15. attendance_records (→ attendance_sessions, student_profiles)
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["attendance_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 16. feedback_staff (→ staff_profiles, student_profiles)
    op.create_table(
        "feedback_staff",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 17. feedback_students (→ student_profiles, staff_profiles)
    op.create_table(
        "feedback_students",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 18. leave_requests (→ users, staff_profiles)
    op.create_table(
        "leave_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["staff_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 19. notifications (→ users)
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])

    # 20. audit_logs (→ users)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_resource_type", "audit_logs")
    op.drop_index("ix_audit_logs_action", "audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_notifications_recipient_id", "notifications")
    op.drop_table("notifications")
    op.drop_table("leave_requests")
    op.drop_table("feedback_students")
    op.drop_table("feedback_staff")
    op.drop_table("attendance_records")
    op.drop_index("ix_attendance_sessions_date", "attendance_sessions")
    op.drop_table("attendance_sessions")
    op.drop_table("assignment_submissions")
    op.drop_table("quiz_results")
    op.drop_table("quiz_attempts")
    op.drop_table("questions")
    op.drop_table("assignments")
    op.drop_table("quizzes")
    op.drop_table("subjects")
    op.drop_table("student_profiles")
    op.drop_table("classrooms")
    op.drop_table("staff_profiles")
    op.drop_table("session_years")
    op.drop_table("departments")
    op.drop_table("users")
