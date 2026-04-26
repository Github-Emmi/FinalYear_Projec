"""Analytics service: aggregated stats for students, staff, and classrooms."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.factory import RepositoryFactory


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repos = RepositoryFactory(session)

    async def student_summary(self, student_id: UUID) -> dict:
        """Return a summary dict for one student.

        Includes:
        - attendance: total, present, absent, late, excused, attendance_pct
        - quizzes: attempts, avg_score, best_score
        - assignments: submissions, graded, avg_score
        """
        # Attendance
        all_records = await self._repos.attendance_records.get_all(limit=50000)
        student_records = [r for r in all_records if r.student_id == student_id]
        total_att = len(student_records)
        present = sum(1 for r in student_records if r.status == "present")

        # Quiz attempts
        quiz_attempts = await self._repos.quiz_attempts.get_all(limit=50000)
        my_attempts = [a for a in quiz_attempts if a.student_id == student_id and a.score is not None]
        quiz_scores = [a.score for a in my_attempts]

        # Assignment submissions
        submissions = await self._repos.submissions.get_all(limit=50000)
        my_subs = [s for s in submissions if s.student_id == student_id]
        graded_subs = [s for s in my_subs if s.score is not None]
        assign_scores = [s.score for s in graded_subs]

        return {
            "student_id": str(student_id),
            "attendance": {
                "total": total_att,
                "present": present,
                "absent": sum(1 for r in student_records if r.status == "absent"),
                "late": sum(1 for r in student_records if r.status == "late"),
                "excused": sum(1 for r in student_records if r.status == "excused"),
                "attendance_pct": round(present / total_att * 100, 1) if total_att else 0.0,
            },
            "quizzes": {
                "attempts": len(my_attempts),
                "avg_score": round(sum(quiz_scores) / len(quiz_scores), 2) if quiz_scores else 0.0,
                "best_score": max(quiz_scores, default=0.0),
            },
            "assignments": {
                "submitted": len(my_subs),
                "graded": len(graded_subs),
                "avg_score": round(sum(assign_scores) / len(assign_scores), 2) if assign_scores else 0.0,
            },
        }

    async def classroom_summary(self, classroom_id: UUID) -> dict:
        """Return aggregated stats for a classroom."""
        all_students = await self._repos.students.get_by_classroom(
            classroom_id, skip=0, limit=50000
        )
        all_sessions = await self._repos.attendance_sessions.get_all(limit=50000)
        classroom_sessions = [s for s in all_sessions if s.classroom_id == classroom_id]

        student_ids = {s.id for s in all_students}
        all_records = await self._repos.attendance_records.get_all(limit=50000)
        classroom_records = [r for r in all_records if r.session_id in {s.id for s in classroom_sessions}]

        return {
            "classroom_id": str(classroom_id),
            "student_count": len(all_students),
            "attendance_sessions": len(classroom_sessions),
            "total_attendance_records": len(classroom_records),
            "overall_present_pct": (
                round(
                    sum(1 for r in classroom_records if r.status == "present")
                    / len(classroom_records)
                    * 100,
                    1,
                )
                if classroom_records
                else 0.0
            ),
        }

    async def staff_summary(self, staff_id: UUID) -> dict:
        """Return aggregated stats for a staff member."""
        subjects = await self._repos.subjects.get_all(limit=50000)
        staff_subjects = [s for s in subjects if s.staff_id == staff_id]

        quizzes = await self._repos.quizzes.get_all(limit=50000)
        staff_quizzes = [q for q in quizzes if q.staff_id == staff_id]

        assignments = await self._repos.assignments.get_all(limit=50000)
        staff_assignments = [a for a in assignments if a.staff_id == staff_id]

        return {
            "staff_id": str(staff_id),
            "subjects_taught": len(staff_subjects),
            "quizzes_created": len(staff_quizzes),
            "assignments_created": len(staff_assignments),
        }

    async def platform_summary(self) -> dict:
        """Return platform-wide stats for the admin dashboard."""
        from datetime import date
        from sqlalchemy import func, select
        from app.models.user import User
        from app.models.student import StudentProfile
        from app.models.staff import StaffProfile
        from app.models.academic import ClassRoom
        from app.models.assignment import Assignment
        from app.models.assessment import Quiz, QuizAttempt
        from app.models.assignment import AssignmentSubmission
        from app.models.notification import Notification

        session = self._repos._session

        total_users = (await session.execute(select(func.count()).select_from(User).where(User.is_deleted.is_(False)))).scalar_one()
        total_students = (await session.execute(select(func.count()).select_from(StudentProfile).where(StudentProfile.is_deleted.is_(False)))).scalar_one()
        total_staff = (await session.execute(select(func.count()).select_from(StaffProfile).where(StaffProfile.is_deleted.is_(False)))).scalar_one()
        total_classrooms = (await session.execute(select(func.count()).select_from(ClassRoom).where(ClassRoom.is_deleted.is_(False)))).scalar_one()
        total_assignments = (await session.execute(select(func.count()).select_from(Assignment).where(Assignment.is_deleted.is_(False)))).scalar_one()
        total_quizzes = (await session.execute(select(func.count()).select_from(Quiz).where(Quiz.is_deleted.is_(False)))).scalar_one()

        today = date.today()
        from sqlalchemy import cast, Date
        submissions_today = (await session.execute(
            select(func.count()).select_from(AssignmentSubmission)
            .where(
                AssignmentSubmission.is_deleted.is_(False),
                cast(AssignmentSubmission.created_at, Date) == today,
            )
        )).scalar_one()

        grading_queue = (await session.execute(
            select(func.count()).select_from(AssignmentSubmission)
            .where(
                AssignmentSubmission.is_deleted.is_(False),
                AssignmentSubmission.score.is_(None),
            )
        )).scalar_one()

        return {
            "total_users": total_users,
            "total_students": total_students,
            "total_staff": total_staff,
            "total_classrooms": total_classrooms,
            "total_assignments": total_assignments,
            "total_quizzes": total_quizzes,
            "active_sessions": 0,
            "submissions_today": submissions_today,
            "grading_queue": grading_queue,
        }
