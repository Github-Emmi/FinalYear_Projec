"""
Attendance Service - Tracks student attendance and generates attendance reports.

Provides methods for:
- Marking attendance by staff for classes
- Calculating attendance percentages with weighted scoring
- Identifying chronic absentees
- Generating attendance reports for students and classes
"""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Attendance,
    AttendanceReport,
    Student,
    Subject,
    Notification,
    SessionYear,
)
from app.schemas import (
    AttendanceResponse,
    AttendanceRecordSchema,
    ClassAttendanceReport,
)
from app.utils.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError,
    ConflictError,
)
from app.services.base_service import BaseService
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)

# Attendance Status Constants
VALID_ATTENDANCE_STATUS = {"PRESENT", "ABSENT", "LATE", "EXCUSED"}


class AttendanceService(BaseService[Attendance]):
    """
    Service for managing student attendance tracking and reporting.
    
    Handles marking attendance, calculating percentages, and generating
    attendance reports with support for attendance policies and chronic
    absentee identification.
    """

    def __init__(self, session: AsyncSession, repos: RepositoryFactory):
        """Initialize AttendanceService with database session and repositories."""
        super().__init__(Attendance, session, repos)
        self.logger = logger

    async def mark_attendance(
        self,
        staff_id: UUID,
        subject_id: UUID,
        class_id: UUID,
        attendance_date: date,
        attendance_records: List[dict],
    ) -> dict:
        """
        Mark attendance for multiple students in a class.

        Args:
            staff_id: UUID of staff member marking attendance
            subject_id: UUID of subject for which attendance is being marked
            class_id: UUID of class for which attendance is being marked
            attendance_date: Date of attendance to mark
            attendance_records: List of {student_id, status, notes} dicts

        Returns:
            {attendance_id, total_marked, students_marked}

        Raises:
            ForbiddenError: If staff doesn't teach this class
            ValidationError: If invalid status or duplicate attendance
            NotFoundError: If subject, class, or student not found
        """
        try:
            # Validate staff teaches this class
            staff = await self.repos.user.get_by_id(staff_id)
            if not staff or staff.role != "STAFF":
                raise ForbiddenError("Only staff can mark attendance")

            staff_classes = await self.repos.staff_class.get_by_staff(staff_id)
            if not any(sc.class_id == class_id for sc in staff_classes):
                raise ForbiddenError("Staff does not teach this class")

            # Validate subject exists
            subject = await self.repos.subject.get_by_id(subject_id)
            if not subject:
                raise NotFoundError(f"Subject {subject_id} not found")

            # Check if attendance already marked for this date
            existing = await self.repos.attendance.get_by_date_and_class(
                attendance_date, class_id
            )
            if existing:
                raise ConflictError(
                    f"Attendance already marked for {attendance_date} in this class"
                )

            # Validate all students enrolled in class
            for record in attendance_records:
                student_id = record.get("student_id")
                student = await self.repos.student.get_by_id(student_id)
                if not student or student.current_class_id != class_id:
                    raise ValidationError(
                        f"Student {student_id} not enrolled in this class"
                    )

                status = record.get("status", "").upper()
                if status not in VALID_ATTENDANCE_STATUS:
                    raise ValidationError(
                        f"Invalid attendance status: {status}. Must be one of {VALID_ATTENDANCE_STATUS}"
                    )

            # Create Attendance record
            async with self.transaction():
                attendance = await self.repos.attendance.create(
                    {
                        "subject_id": subject_id,
                        "class_id": class_id,
                        "attendance_date": attendance_date,
                        "marked_by": staff_id,
                        "marked_at": datetime.now(),
                    }
                )

                # Create AttendanceReport for each student
                student_count = 0
                for record in attendance_records:
                    await self.repos.attendance_report.create(
                        {
                            "attendance_id": attendance.id,
                            "student_id": record.get("student_id"),
                            "status": record.get("status", "").upper(),
                            "notes": record.get("notes"),
                        }
                    )
                    student_count += 1

                # Log audit trail
                self.log_action(
                    action="MARK_ATTENDANCE",
                    entity_type="Attendance",
                    entity_id=str(attendance.id),
                    user_id=str(staff_id),
                    changes={
                        "subject_id": str(subject_id),
                        "class_id": str(class_id),
                        "attendance_date": str(attendance_date),
                        "student_count": student_count,
                    },
                )

            return self.success_response(
                data={
                    "attendance_id": str(attendance.id),
                    "total_marked": student_count,
                    "students_marked": student_count,
                    "marked_date": str(attendance_date),
                    "marked_at": attendance.marked_at.isoformat(),
                }
            )

        except (ForbiddenError, ValidationError, NotFoundError, ConflictError):
            raise
        except Exception as e:
            self.logger.error(f"Error marking attendance: {str(e)}")
            raise ValidationError(f"Failed to mark attendance: {str(e)}")

    async def get_student_attendance(
        self, student_id: UUID, session_year_id: UUID
    ) -> dict:
        """
        Get detailed attendance record for a student in a session year.

        Args:
            student_id: UUID of student
            session_year_id: UUID of session year

        Returns:
            {
                student_id,
                session,
                overall_rate,
                by_subject: [{subject, rate}],
                present_days,
                absent_days,
                late_days,
                excused_days
            }

        Raises:
            NotFoundError: If student or session year not found
        """
        try:
            # Validate student exists
            student = await self.repos.student.get_by_id(student_id)
            if not student:
                raise NotFoundError(f"Student {student_id} not found")

            # Validate session year exists
            session = await self.repos.session_year.get_by_id(session_year_id)
            if not session:
                raise NotFoundError(f"Session year {session_year_id} not found")

            # Fetch all attendance reports for student in this session
            attendance_records = (
                await self.repos.attendance_report.get_by_student_and_session(
                    student_id, session_year_id
                )
            )

            if not attendance_records:
                return self.success_response(
                    data={
                        "student_id": str(student_id),
                        "session": session.name,
                        "overall_rate": 0.0,
                        "by_subject": [],
                        "present_days": 0,
                        "absent_days": 0,
                        "late_days": 0,
                        "excused_days": 0,
                    }
                )

            # Group by subject and calculate rates
            subject_stats = {}
            present_count = 0
            absent_count = 0
            late_count = 0
            excused_count = 0

            for record in attendance_records:
                subject_id = str(record.attendance.subject_id)
                status = record.status

                # Count status
                if status == "PRESENT":
                    present_count += 1
                elif status == "ABSENT":
                    absent_count += 1
                elif status == "LATE":
                    late_count += 1
                elif status == "EXCUSED":
                    excused_count += 1

                # Group by subject
                if subject_id not in subject_stats:
                    subject_stats[subject_id] = {
                        "subject_name": record.attendance.subject.name,
                        "present": 0,
                        "absent": 0,
                        "late": 0,
                        "excused": 0,
                        "total": 0,
                    }

                if status == "PRESENT":
                    subject_stats[subject_id]["present"] += 1
                elif status == "ABSENT":
                    subject_stats[subject_id]["absent"] += 1
                elif status == "LATE":
                    subject_stats[subject_id]["late"] += 1
                elif status == "EXCUSED":
                    subject_stats[subject_id]["excused"] += 1

                subject_stats[subject_id]["total"] += 1

            # Calculate percentages
            total_days = len(attendance_records)
            overall_rate = (present_count + excused_count) / total_days * 100 if total_days > 0 else 0.0

            by_subject = []
            for subject_id, stats in subject_stats.items():
                subject_total = stats["total"]
                subject_rate = (
                    (stats["present"] + stats["excused"]) / subject_total * 100
                    if subject_total > 0
                    else 0.0
                )
                by_subject.append(
                    {
                        "subject_id": subject_id,
                        "subject_name": stats["subject_name"],
                        "attendance_rate": round(subject_rate, 2),
                        "days_present": stats["present"],
                        "days_absent": stats["absent"],
                        "days_late": stats["late"],
                        "days_excused": stats["excused"],
                    }
                )

            return self.success_response(
                data={
                    "student_id": str(student_id),
                    "student_name": f"{student.user.first_name} {student.user.last_name}",
                    "session": session.name,
                    "overall_rate": round(overall_rate, 2),
                    "by_subject": by_subject,
                    "present_days": present_count,
                    "absent_days": absent_count,
                    "late_days": late_count,
                    "excused_days": excused_count,
                    "total_days": total_days,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error fetching student attendance: {str(e)}")
            raise ValidationError(f"Failed to fetch attendance: {str(e)}")

    async def calculate_attendance_percentage(
        self,
        student_id: UUID,
        subject_id: Optional[UUID] = None,
        session_year_id: Optional[UUID] = None,
    ) -> float:
        """
        Calculate weighted attendance percentage for a student.

        Scoring: PRESENT=1, LATE=0.5, EXCUSED=1, ABSENT=0

        Args:
            student_id: UUID of student
            subject_id: Optional UUID of specific subject (None = all subjects)
            session_year_id: Optional UUID of specific session (None = current)

        Returns:
            Attendance percentage (0.0-100.0)

        Raises:
            NotFoundError: If student not found
        """
        try:
            # Validate student exists
            student = await self.repos.student.get_by_id(student_id)
            if not student:
                raise NotFoundError(f"Student {student_id} not found")

            # Use current session if not specified
            if not session_year_id:
                current_session = await self.repos.session_year.get_current()
                if not current_session:
                    return 0.0
                session_year_id = current_session.id

            # Fetch attendance records
            if subject_id and session_year_id:
                attendance_records = (
                    await self.repos.attendance_report.get_by_student_subject_session(
                        student_id, subject_id, session_year_id
                    )
                )
            elif session_year_id:
                attendance_records = (
                    await self.repos.attendance_report.get_by_student_and_session(
                        student_id, session_year_id
                    )
                )
            else:
                return 0.0

            if not attendance_records:
                return 0.0

            # Calculate weighted score
            weighted_score = 0.0
            for record in attendance_records:
                if record.status == "PRESENT":
                    weighted_score += 1.0
                elif record.status == "LATE":
                    weighted_score += 0.5
                elif record.status == "EXCUSED":
                    weighted_score += 1.0
                # ABSENT = 0

            percentage = (weighted_score / len(attendance_records)) * 100
            return round(percentage, 2)

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error calculating attendance percentage: {str(e)}")
            raise ValidationError(f"Failed to calculate percentage: {str(e)}")

    async def mark_chronic_absentees(
        self, session_year_id: UUID, threshold: int = 25
    ) -> dict:
        """
        Identify and flag chronic absentees (attendance below threshold).

        Args:
            session_year_id: UUID of session year
            threshold: Attendance percentage threshold (default 25%)

        Returns:
            {total_flagged, student_ids}

        Raises:
            ValidationError: If threshold invalid or session not found
        """
        try:
            # Validate threshold
            if not (0 < threshold <= 100):
                raise ValidationError("Threshold must be between 0 and 100")

            # Validate session year exists
            session = await self.repos.session_year.get_by_id(session_year_id)
            if not session:
                raise NotFoundError(f"Session year {session_year_id} not found")

            # Get all students in session
            students = await self.repos.student.get_by_session(session_year_id)

            flagged_students = []
            async with self.transaction():
                for student in students:
                    # Calculate attendance percentage
                    percentage = await self.calculate_attendance_percentage(
                        student.id, session_year_id=session_year_id
                    )

                    # Flag if below threshold
                    if percentage < threshold:
                        flagged_students.append(student.id)

                        # Create/update chronic absentee record
                        await self.repos.chronic_absentee.create_or_update(
                            {
                                "student_id": student.id,
                                "session_year_id": session_year_id,
                                "attendance_percentage": percentage,
                                "flag_date": datetime.now(),
                                "notified": True,
                            }
                        )

                        # Send notification to student
                        await self.repos.notification.create(
                            {
                                "user_id": student.user_id,
                                "title": "Chronic Absentee Alert",
                                "message": f"Your attendance ({percentage:.1f}%) is below threshold ({threshold}%). Please contact administration.",
                                "type": "ALERT",
                                "data": {
                                    "student_id": str(student.id),
                                    "attendance_percentage": percentage,
                                    "threshold": threshold,
                                },
                            }
                        )

                        # Send notification to admin
                        admins = await self.repos.user.get_by_role("ADMIN")
                        for admin in admins:
                            await self.repos.notification.create(
                                {
                                    "user_id": admin.id,
                                    "title": "Chronic Absentee Report",
                                    "message": f"Student {student.user.first_name} {student.user.last_name} flagged as chronic absentee (Attendance: {percentage:.1f}%)",
                                    "type": "WARNING",
                                    "data": {
                                        "student_id": str(student.id),
                                        "student_name": f"{student.user.first_name} {student.user.last_name}",
                                        "attendance_percentage": percentage,
                                    },
                                }
                            )

                # Log audit trail
                self.log_action(
                    action="MARK_CHRONIC_ABSENTEES",
                    entity_type="ChronicAbsentee",
                    entity_id="BATCH",
                    user_id="SYSTEM",
                    changes={
                        "session_year_id": str(session_year_id),
                        "threshold": threshold,
                        "total_flagged": len(flagged_students),
                        "flagged_student_ids": [str(sid) for sid in flagged_students],
                    },
                )

            return self.success_response(
                data={
                    "total_flagged": len(flagged_students),
                    "student_ids": [str(sid) for sid in flagged_students],
                    "threshold": threshold,
                    "session_year_id": str(session_year_id),
                }
            )

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Error marking chronic absentees: {str(e)}")
            raise ValidationError(f"Failed to mark chronic absentees: {str(e)}")

    async def generate_attendance_report(
        self, class_id: UUID, start_date: date, end_date: date
    ) -> dict:
        """
        Generate comprehensive attendance report for a class.

        Args:
            class_id: UUID of class
            start_date: Report start date
            end_date: Report end date

        Returns:
            {
                class_id,
                class_name,
                period: {start_date, end_date},
                total_students,
                attendance_stats: {...},
                absentee_list: [...],
                late_list: [...],
                subject_wise: [...]
            }

        Raises:
            ValidationError: If dates invalid or class not found
        """
        try:
            # Validate dates
            if start_date > end_date:
                raise ValidationError("Start date must be before end date")

            # Get class
            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            # Get all students in class
            students = await self.repos.student.get_by_class(class_id)

            # Fetch attendance records for date range
            attendance_records = await self.repos.attendance.get_by_class_and_date_range(
                class_id, start_date, end_date
            )

            # Build report
            student_data = {}
            subject_wise_stats = {}
            absentee_list = []
            late_list = []

            for student in students:
                student_data[student.id] = {
                    "student_name": f"{student.user.first_name} {student.user.last_name}",
                    "total_days": 0,
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "excused": 0,
                    "attendance_rate": 0.0,
                }

            # Process attendance records
            for record in attendance_records:
                for report in record.attendance_reports:
                    if report.student_id in student_data:
                        student_data[report.student_id]["total_days"] += 1

                        if report.status == "PRESENT":
                            student_data[report.student_id]["present"] += 1
                        elif report.status == "ABSENT":
                            student_data[report.student_id]["absent"] += 1
                            absentee_list.append(
                                {
                                    "student_id": str(report.student_id),
                                    "student_name": student_data[report.student_id][
                                        "student_name"
                                    ],
                                    "date": str(record.attendance_date),
                                    "notes": report.notes,
                                }
                            )
                        elif report.status == "LATE":
                            student_data[report.student_id]["late"] += 1
                            late_list.append(
                                {
                                    "student_id": str(report.student_id),
                                    "student_name": student_data[report.student_id][
                                        "student_name"
                                    ],
                                    "date": str(record.attendance_date),
                                }
                            )
                        elif report.status == "EXCUSED":
                            student_data[report.student_id]["excused"] += 1

                    # Aggregate subject-wise
                    subject_id = str(record.subject_id)
                    if subject_id not in subject_wise_stats:
                        subject_wise_stats[subject_id] = {
                            "subject_name": record.subject.name,
                            "total_records": 0,
                            "present": 0,
                            "absent": 0,
                            "late": 0,
                        }

                    subject_wise_stats[subject_id]["total_records"] += 1
                    if report.status == "PRESENT":
                        subject_wise_stats[subject_id]["present"] += 1
                    elif report.status == "ABSENT":
                        subject_wise_stats[subject_id]["absent"] += 1
                    elif report.status == "LATE":
                        subject_wise_stats[subject_id]["late"] += 1

            # Calculate rates
            for student_id in student_data:
                total = student_data[student_id]["total_days"]
                if total > 0:
                    present_weighted = (
                        student_data[student_id]["present"]
                        + student_data[student_id]["excused"]
                    ) / total
                    student_data[student_id]["attendance_rate"] = (
                        round(present_weighted * 100, 2)
                    )

            # Aggregate statistics
            attendance_stats = {
                "total_days_marked": len(attendance_records),
                "total_students": len(students),
                "average_attendance_rate": (
                    sum(s["attendance_rate"] for s in student_data.values())
                    / len(students)
                    if students
                    else 0.0
                ),
                "total_absences": len(absentee_list),
                "total_late": len(late_list),
            }

            return self.success_response(
                data={
                    "class_id": str(class_id),
                    "class_name": cls.name,
                    "period": {"start_date": str(start_date), "end_date": str(end_date)},
                    "total_students": len(students),
                    "attendance_stats": attendance_stats,
                    "student_wise": list(student_data.values()),
                    "absentee_list": absentee_list,
                    "late_list": late_list,
                    "subject_wise": list(subject_wise_stats.values()),
                    "generated_at": datetime.now().isoformat(),
                }
            )

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Error generating attendance report: {str(e)}")
            raise ValidationError(f"Failed to generate report: {str(e)}")
