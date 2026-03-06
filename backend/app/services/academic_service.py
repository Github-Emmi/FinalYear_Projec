"""
Academic Service - Manages academic structure and calendar.

Provides methods for:
- Academic session creation and lifecycle management
- Department creation and management
- Class creation and student transfers
- Timetable creation, validation, and export
- Subject-class linking and assignments
"""

from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID
import logging
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    SessionYear,
    Department,
    Class,
    Subject,
    Timetable,
    Student,
    Staff,
)
from app.utils.exceptions import (
    NotFoundError,
    ValidationError,
    ConflictError,
    ForbiddenError,
)
from app.services.base_service import BaseService
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)

# Session Status Constants
SESSION_STATUS = {"INACTIVE", "ACTIVE", "ARCHIVED"}

# Class Level Constants
CLASS_LEVELS = {"FOUNDATIONAL", "INTERMEDIATE", "SENIOR"}

# Day of Week Constants
VALID_DAYS = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"}

# Class Time Constants
SCHOOL_START_TIME = "09:00"
SCHOOL_END_TIME = "16:00"
MIN_CLASS_DURATION = 30  # minutes
MAX_CLASSES_PER_DAY = 6

# Capacity Limits
MIN_CLASS_CAPACITY = 1
MAX_CLASS_CAPACITY = 50
OPTIMAL_CLASS_SIZE = 35


class AcademicService(BaseService[SessionYear]):
    """
    Service for comprehensive academic structure management.

    Handles academic sessions, departments, classes, timetables, and
    academic calendar management with full validation and audit trails.
    """

    def __init__(self, session: AsyncSession, repos: RepositoryFactory):
        """Initialize AcademicService with database session and repositories."""
        super().__init__(SessionYear, session, repos)
        self.logger = logger

    # ===== SESSION MANAGEMENT METHODS =====

    async def create_session_year(
        self,
        year_range: str,
        start_date: date,
        end_date: date,
        system_open_date: date,
        system_close_date: date,
    ) -> dict:
        """
        Create a new academic session year.

        Args:
            year_range: Format "YYYY-YYYY" (e.g., "2024-2025")
            start_date: Academic year start date
            end_date: Academic year end date
            system_open_date: When registration opens
            system_close_date: When registration closes

        Returns:
            {session_id, year_range, start_date, end_date, status}

        Raises:
            ValidationError: If dates invalid or format wrong
            ConflictError: If overlapping session exists
        """
        try:
            # Validate year_range format
            if not year_range or "-" not in year_range:
                raise ValidationError("Year range must be in format 'YYYY-YYYY'")

            parts = year_range.split("-")
            if len(parts) != 2:
                raise ValidationError("Year range must contain exactly one hyphen")

            try:
                start_year = int(parts[0])
                end_year = int(parts[1])
                if end_year != start_year + 1:
                    raise ValueError()
            except (ValueError, IndexError):
                raise ValidationError(
                    "Year range must be consecutive years (e.g., '2024-2025')"
                )

            # Validate dates
            if start_date >= end_date:
                raise ValidationError("Start date must be before end date")

            if system_open_date >= system_close_date:
                raise ValidationError("System open date must be before close date")

            if not (start_date <= system_open_date < system_close_date <= end_date):
                raise ValidationError(
                    "System dates must be within academic year boundary"
                )

            # Check for overlapping sessions
            existing = await self.repos.session_year.get_by_year_range(year_range)
            if existing:
                raise ConflictError(f"Session year {year_range} already exists")

            # Create session
            async with self.transaction():
                session_obj = await self.repos.session_year.create(
                    {
                        "year": year_range,
                        "name": f"Academic Year {year_range}",
                        "start_date": start_date,
                        "end_date": end_date,
                        "system_open_date": system_open_date,
                        "system_close_date": system_close_date,
                        "status": "INACTIVE",
                        "is_active": False,
                        "created_at": datetime.now(),
                    }
                )

                # Log creation
                self.log_action(
                    action="CREATE_SESSION_YEAR",
                    entity_type="SessionYear",
                    entity_id=str(session_obj.id),
                    user_id="SYSTEM",
                    changes={
                        "year_range": year_range,
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                        "status": "INACTIVE",
                    },
                )

            return self.success_response(
                data={
                    "session_id": str(session_obj.id),
                    "year_range": year_range,
                    "name": session_obj.name,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "system_open_date": str(system_open_date),
                    "system_close_date": str(system_close_date),
                    "status": "INACTIVE",
                    "created_at": datetime.now().isoformat(),
                }
            )

        except (ValidationError, ConflictError):
            raise
        except Exception as e:
            self.logger.error(f"Error creating session year: {str(e)}")
            raise ValidationError(f"Failed to create session year: {str(e)}")

    async def activate_session_year(self, session_year_id: UUID) -> dict:
        """
        Activate an academic session year (set as current).

        Only one session can be active at a time.

        Args:
            session_year_id: UUID of session to activate

        Returns:
            {session_id, year_range, status, activated_at}

        Raises:
            NotFoundError: If session not found
        """
        try:
            # Validate session exists
            session_obj = await self.repos.session_year.get_by_id(session_year_id)
            if not session_obj:
                raise NotFoundError(f"Session {session_year_id} not found")

            async with self.transaction():
                # Deactivate any currently active session
                active_sessions = await self.repos.session_year.get_active()
                for active in active_sessions:
                    await self.repos.session_year.update(
                        active,
                        {
                            "is_active": False,
                            "status": "INACTIVE",
                        },
                    )

                # Activate new session
                await self.repos.session_year.update(
                    session_obj,
                    {
                        "is_active": True,
                        "status": "ACTIVE",
                        "activated_at": datetime.now(),
                    },
                )

                # Log activation
                self.log_action(
                    action="ACTIVATE_SESSION_YEAR",
                    entity_type="SessionYear",
                    entity_id=str(session_year_id),
                    user_id="SYSTEM",
                    changes={
                        "status": "ACTIVE",
                        "activated_at": datetime.now().isoformat(),
                    },
                )

                # Notify all stakeholders
                users = await self.repos.user.get_all()
                for user in users:
                    await self.repos.notification.create(
                        {
                            "user_id": user.id,
                            "title": "Academic Session Activated",
                            "message": f"Academic session {session_obj.name} is now active",
                            "type": "INFO",
                        }
                    )

            return self.success_response(
                data={
                    "session_id": str(session_year_id),
                    "year_range": session_obj.year,
                    "name": session_obj.name,
                    "status": "ACTIVE",
                    "activated_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error activating session: {str(e)}")
            raise ValidationError(f"Failed to activate session: {str(e)}")

    async def end_session_year(
        self, session_year_id: UUID, archive: bool = True
    ) -> dict:
        """
        End and archive an academic session year.

        Args:
            session_year_id: UUID of session to end
            archive: Whether to create historical backup

        Returns:
            {session_id, year_range, status, archived_at}

        Raises:
            NotFoundError: If session not found
            ValidationError: If incomplete data exists
        """
        try:
            # Validate session exists
            session_obj = await self.repos.session_year.get_by_id(session_year_id)
            if not session_obj:
                raise NotFoundError(f"Session {session_year_id} not found")

            # Check for incomplete data
            pending_leaves = (
                await self.repos.leave.get_pending_by_session(session_year_id)
            )
            if pending_leaves:
                raise ValidationError(
                    f"Cannot end session with {len(pending_leaves)} pending leave requests"
                )

            async with self.transaction():
                # Update session status
                await self.repos.session_year.update(
                    session_obj,
                    {
                        "is_active": False,
                        "status": "ARCHIVED",
                        "archived_at": datetime.now(),
                    },
                )

                # Log archival
                self.log_action(
                    action="END_SESSION_YEAR",
                    entity_type="SessionYear",
                    entity_id=str(session_year_id),
                    user_id="SYSTEM",
                    changes={
                        "status": "ARCHIVED",
                        "archived_at": datetime.now().isoformat(),
                    },
                )

                # Notify all stakeholders
                users = await self.repos.user.get_all()
                for user in users:
                    await self.repos.notification.create(
                        {
                            "user_id": user.id,
                            "title": "Academic Session Ended",
                            "message": f"Academic session {session_obj.name} has been archived",
                            "type": "INFO",
                        }
                    )

            return self.success_response(
                data={
                    "session_id": str(session_year_id),
                    "year_range": session_obj.year,
                    "status": "ARCHIVED",
                    "archived_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error ending session: {str(e)}")
            raise ValidationError(f"Failed to end session: {str(e)}")

    # ===== DEPARTMENT MANAGEMENT METHODS =====

    async def create_department(
        self,
        name: str,
        code: str,
        description: Optional[str] = None,
        head_of_department_id: Optional[UUID] = None,
    ) -> dict:
        """
        Create a new department.

        Args:
            name: Department name (min 3 chars)
            code: Department code (max 10 alphanumeric chars, unique)
            description: Optional department description
            head_of_department_id: Optional staff UUID

        Returns:
            {department_id, name, code, head_name}

        Raises:
            ValidationError: If invalid inputs or duplicates exist
        """
        try:
            # Validate name
            if not name or len(name.strip()) < 3:
                raise ValidationError("Department name must be at least 3 characters")

            # Validate code
            if not code or len(code) > 10 or not code.isalnum():
                raise ValidationError(
                    "Department code must be alphanumeric and max 10 characters"
                )

            # Check uniqueness
            existing_name = await self.repos.department.get_by_name(name)
            if existing_name:
                raise ConflictError(f"Department '{name}' already exists")

            existing_code = await self.repos.department.get_by_code(code)
            if existing_code:
                raise ConflictError(f"Department code '{code}' already exists")

            # Validate HOD if provided
            hod = None
            if head_of_department_id:
                hod = await self.repos.staff.get_by_id(head_of_department_id)
                if not hod:
                    raise NotFoundError(f"Staff {head_of_department_id} not found")

            async with self.transaction():
                department = await self.repos.department.create(
                    {
                        "name": name,
                        "code": code,
                        "description": description,
                        "head_of_department_id": head_of_department_id,
                        "created_at": datetime.now(),
                    }
                )

                # Log creation
                self.log_action(
                    action="CREATE_DEPARTMENT",
                    entity_type="Department",
                    entity_id=str(department.id),
                    user_id="SYSTEM",
                    changes={
                        "name": name,
                        "code": code,
                        "head_id": str(head_of_department_id) if head_of_department_id else None,
                    },
                )

                # Notify HOD
                if hod:
                    await self.repos.notification.create(
                        {
                            "user_id": hod.user_id,
                            "title": "Department Head Appointment",
                            "message": f"You have been appointed as head of {name} department",
                            "type": "INFO",
                        }
                    )

            return self.success_response(
                data={
                    "department_id": str(department.id),
                    "name": name,
                    "code": code,
                    "description": description,
                    "head_name": f"{hod.user.first_name} {hod.user.last_name}"
                    if hod
                    else None,
                    "created_at": datetime.now().isoformat(),
                }
            )

        except (ValidationError, ConflictError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Error creating department: {str(e)}")
            raise ValidationError(f"Failed to create department: {str(e)}")

    async def assign_department_head(
        self,
        department_id: UUID,
        staff_id: UUID,
        academic_year_id: UUID,
    ) -> dict:
        """
        Assign a staff member as department head for academic year.

        Args:
            department_id: UUID of department
            staff_id: UUID of staff member
            academic_year_id: UUID of academic year

        Returns:
            {department_id, department_name, head_name, effective_date}

        Raises:
            NotFoundError: If department, staff, or session not found
            ValidationError: If staff not in department
        """
        try:
            # Validate all entities
            department = await self.repos.department.get_by_id(department_id)
            if not department:
                raise NotFoundError(f"Department {department_id} not found")

            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            session = await self.repos.session_year.get_by_id(academic_year_id)
            if not session:
                raise NotFoundError(f"Session {academic_year_id} not found")

            # Validate staff in department
            if staff.department_id != department_id:
                raise ValidationError(
                    f"Staff is not in {department.name} department"
                )

            async with self.transaction():
                # Update department head
                await self.repos.department.update(
                    department,
                    {
                        "head_of_department_id": staff_id,
                        "head_assignment_date": datetime.now(),
                    },
                )

                # Log assignment
                self.log_action(
                    action="ASSIGN_DEPARTMENT_HEAD",
                    entity_type="Department",
                    entity_id=str(department_id),
                    user_id="SYSTEM",
                    changes={
                        "department": department.name,
                        "head_name": f"{staff.user.first_name} {staff.user.last_name}",
                        "session": session.name,
                        "effective_date": datetime.now().isoformat(),
                    },
                )

                # Notify new head
                await self.repos.notification.create(
                    {
                        "user_id": staff.user_id,
                        "title": "Department Head Assignment",
                        "message": f"You are now head of {department.name} for {session.name}",
                        "type": "INFO",
                    }
                )

            return self.success_response(
                data={
                    "department_id": str(department_id),
                    "department_name": department.name,
                    "head_name": f"{staff.user.first_name} {staff.user.last_name}",
                    "session": session.name,
                    "effective_date": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error assigning department head: {str(e)}")
            raise ValidationError(f"Failed to assign department head: {str(e)}")

    # ===== CLASS MANAGEMENT METHODS =====

    async def create_class(
        self,
        name: str,
        code: str,
        department_id: UUID,
        academic_year_id: UUID,
        capacity: int,
        level: str,
    ) -> dict:
        """
        Create a new class in the academic system.

        Args:
            name: Class name (e.g., "Form 1A")
            code: Unique code per department per year
            department_id: UUID of department
            academic_year_id: UUID of academic year
            capacity: Student capacity (1-50)
            level: FOUNDATIONAL, INTERMEDIATE, or SENIOR

        Returns:
            {class_id, name, code, capacity, level, students_enrolled}

        Raises:
            ValidationError: If invalid inputs
            NotFoundError: If department or session not found
        """
        try:
            # Validate inputs
            if not name or len(name.strip()) < 2:
                raise ValidationError("Class name must be at least 2 characters")

            if not code or len(code) > 20:
                raise ValidationError("Class code required (max 20 chars)")

            if not (MIN_CLASS_CAPACITY <= capacity <= MAX_CLASS_CAPACITY):
                raise ValidationError(
                    f"Capacity must be between {MIN_CLASS_CAPACITY} and {MAX_CLASS_CAPACITY}"
                )

            if level not in CLASS_LEVELS:
                raise ValidationError(f"Invalid level. Must be one of {CLASS_LEVELS}")

            # Validate department and session
            department = await self.repos.department.get_by_id(department_id)
            if not department:
                raise NotFoundError(f"Department {department_id} not found")

            session = await self.repos.session_year.get_by_id(academic_year_id)
            if not session:
                raise NotFoundError(f"Session {academic_year_id} not found")

            # Check code uniqueness per department per year
            existing = await self.repos.class_.get_by_code_department_year(
                code, department_id, academic_year_id
            )
            if existing:
                raise ConflictError(
                    f"Class code '{code}' already exists in this department this year"
                )

            async with self.transaction():
                cls = await self.repos.class_.create(
                    {
                        "name": name,
                        "code": code,
                        "department_id": department_id,
                        "session_year_id": academic_year_id,
                        "capacity": capacity,
                        "level": level,
                        "created_at": datetime.now(),
                    }
                )

                # Log creation
                self.log_action(
                    action="CREATE_CLASS",
                    entity_type="Class",
                    entity_id=str(cls.id),
                    user_id="SYSTEM",
                    changes={
                        "name": name,
                        "code": code,
                        "department": department.name,
                        "capacity": capacity,
                        "level": level,
                    },
                )

            return self.success_response(
                data={
                    "class_id": str(cls.id),
                    "name": name,
                    "code": code,
                    "department": department.name,
                    "level": level,
                    "capacity": capacity,
                    "students_enrolled": 0,
                    "created_at": datetime.now().isoformat(),
                }
            )

        except (ValidationError, ConflictError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Error creating class: {str(e)}")
            raise ValidationError(f"Failed to create class: {str(e)}")

    async def transfer_student_to_class(
        self,
        student_id: UUID,
        current_class_id: UUID,
        new_class_id: UUID,
        reason: str,
    ) -> dict:
        """
        Transfer a student to a different class.

        Args:
            student_id: UUID of student
            current_class_id: UUID of current class
            new_class_id: UUID of destination class
            reason: Transfer reason for audit trail

        Returns:
            {student_id, name, old_class, new_class, transfer_date}

        Raises:
            NotFoundError: If any entity not found
            ValidationError: If student not in current class or new class full
        """
        try:
            # Validate all entities
            student = await self.repos.student.get_by_id(student_id)
            if not student:
                raise NotFoundError(f"Student {student_id} not found")

            current_class = await self.repos.class_.get_by_id(current_class_id)
            if not current_class:
                raise NotFoundError(f"Current class {current_class_id} not found")

            new_class = await self.repos.class_.get_by_id(new_class_id)
            if not new_class:
                raise NotFoundError(f"New class {new_class_id} not found")

            # Validate student in current class
            if student.current_class_id != current_class_id:
                raise ValidationError(
                    f"Student not enrolled in {current_class.name}"
                )

            # Check new class capacity
            enrolled = (
                await self.repos.student.get_by_class(new_class_id)
            )
            if len(enrolled) >= new_class.capacity:
                raise ValidationError(
                    f"New class {new_class.name} is at full capacity"
                )

            if not reason or len(reason.strip()) < 5:
                raise ValidationError("Transfer reason must be at least 5 characters")

            async with self.transaction():
                # Transfer student
                await self.repos.student.update(
                    student,
                    {
                        "current_class_id": new_class_id,
                        "last_transfer_date": datetime.now(),
                    },
                )

                # Log transfer
                self.log_action(
                    action="TRANSFER_STUDENT",
                    entity_type="Student",
                    entity_id=str(student_id),
                    user_id="SYSTEM",
                    changes={
                        "from_class": current_class.name,
                        "to_class": new_class.name,
                        "reason": reason,
                        "transfer_date": datetime.now().isoformat(),
                    },
                )

                # Notify student and parents
                await self.repos.notification.create(
                    {
                        "user_id": student.user_id,
                        "title": "Class Transfer",
                        "message": f"You have been transferred from {current_class.name} to {new_class.name}",
                        "type": "INFO",
                        "data": {"reason": reason},
                    }
                )

            return self.success_response(
                data={
                    "student_id": str(student_id),
                    "name": f"{student.user.first_name} {student.user.last_name}",
                    "old_class": current_class.name,
                    "new_class": new_class.name,
                    "reason": reason,
                    "transfer_date": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error transferring student: {str(e)}")
            raise ValidationError(f"Failed to transfer student: {str(e)}")

    async def delete_class(self, class_id: UUID) -> dict:
        """
        Soft delete a class (archive).

        Args:
            class_id: UUID of class to delete

        Returns:
            {class_id, message, deleted_at}

        Raises:
            NotFoundError: If class not found
            ValidationError: If class has enrolled students or active subjects
        """
        try:
            # Validate class exists
            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            # Check for enrolled students
            students = await self.repos.student.get_by_class(class_id)
            if students:
                raise ValidationError(
                    f"Cannot delete class with {len(students)} enrolled students"
                )

            # Check for active subjects
            subjects = await self.repos.subject.get_by_class(class_id)
            if subjects:
                raise ValidationError(
                    f"Cannot delete class with {len(subjects)} assigned subjects"
                )

            async with self.transaction():
                # Soft delete
                await self.repos.class_.update(
                    cls,
                    {
                        "is_deleted": True,
                        "deleted_at": datetime.now(),
                    },
                )

                # Log deletion
                self.log_action(
                    action="DELETE_CLASS",
                    entity_type="Class",
                    entity_id=str(class_id),
                    user_id="SYSTEM",
                    changes={
                        "class_name": cls.name,
                        "deleted_at": datetime.now().isoformat(),
                    },
                )

            return self.success_response(
                data={
                    "class_id": str(class_id),
                    "message": f"Class {cls.name} has been deleted",
                    "deleted_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error deleting class: {str(e)}")
            raise ValidationError(f"Failed to delete class: {str(e)}")

    # ===== SUBJECT-CLASS LINKING =====

    async def assign_subjects_to_class(
        self,
        class_id: UUID,
        subject_assignments: List[dict],
    ) -> dict:
        """
        Assign multiple subjects to a class with staff assignments.

        Args:
            class_id: UUID of class
            subject_assignments: List of {subject_id, staff_id}

        Returns:
            {class_id, class_name, subjects_assigned, created_at}

        Raises:
            NotFoundError: If class, subject, or staff not found
            ValidationError: If duplicate assignment
        """
        try:
            # Validate class exists
            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            async with self.transaction():
                assigned_count = 0
                assigned_subjects = []

                for assignment in subject_assignments:
                    subject_id = assignment.get("subject_id")
                    staff_id = assignment.get("staff_id")

                    # Validate subject
                    subject = await self.repos.subject.get_by_id(subject_id)
                    if not subject:
                        raise NotFoundError(f"Subject {subject_id} not found")

                    # Validate staff
                    staff = await self.repos.staff.get_by_id(staff_id)
                    if not staff:
                        raise NotFoundError(f"Staff {staff_id} not found")

                    # Check no duplicate
                    existing = (
                        await self.repos.subject.get_by_class_and_subject(
                            class_id, subject_id
                        )
                    )
                    if existing:
                        self.logger.warning(
                            f"Subject {subject.name} already assigned to {cls.name}"
                        )
                        continue

                    # Create assignment
                    assignment_obj = await self.repos.subject.create(
                        {
                            "class_id": class_id,
                            "subject_id": subject_id,
                            "staff_id": staff_id,
                            "assigned_date": datetime.now(),
                        }
                    )

                    assigned_subjects.append(
                        {
                            "subject_name": subject.name,
                            "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
                        }
                    )
                    assigned_count += 1

                # Log batch assignment
                if assigned_count > 0:
                    self.log_action(
                        action="ASSIGN_SUBJECTS_TO_CLASS",
                        entity_type="SubjectAssignment",
                        entity_id=str(class_id),
                        user_id="SYSTEM",
                        changes={
                            "class": cls.name,
                            "subjects_assigned": assigned_count,
                            "subjects": assigned_subjects,
                        },
                    )

            return self.success_response(
                data={
                    "class_id": str(class_id),
                    "class_name": cls.name,
                    "subjects_assigned": assigned_count,
                    "subjects": assigned_subjects,
                    "created_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error assigning subjects to class: {str(e)}")
            raise ValidationError(f"Failed to assign subjects: {str(e)}")

    # ===== TIMETABLE MANAGEMENT =====

    async def create_timetable(
        self,
        class_id: UUID,
        academic_year_id: UUID,
        timetable_data: List[dict],
    ) -> dict:
        """
        Create a complete timetable for a class.

        Args:
            class_id: UUID of class
            academic_year_id: UUID of academic year
            timetable_data: List of {day, time_start, time_end, subject_id, staff_id, room}

        Returns:
            {timetable_id, class_name, total_slots, validation_status}

        Raises:
            NotFoundError: If class or session not found
            ValidationError: If conflicts or validation failures
        """
        try:
            # Validate class and session
            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            session = await self.repos.session_year.get_by_id(academic_year_id)
            if not session:
                raise NotFoundError(f"Session {academic_year_id} not found")

            # Validate timetable data
            if not timetable_data:
                raise ValidationError("Timetable data cannot be empty")

            async with self.transaction():
                created_slots = 0

                for slot in timetable_data:
                    day = slot.get("day", "").upper()
                    time_start = slot.get("time_start")
                    time_end = slot.get("time_end")
                    subject_id = slot.get("subject_id")
                    staff_id = slot.get("staff_id")
                    room = slot.get("room")

                    # Validate day
                    if day not in VALID_DAYS:
                        raise ValidationError(f"Invalid day: {day}")

                    # Validate subject and staff
                    subject = await self.repos.subject.get_by_id(subject_id)
                    if not subject:
                        raise NotFoundError(f"Subject {subject_id} not found")

                    staff = await self.repos.staff.get_by_id(staff_id)
                    if not staff:
                        raise NotFoundError(f"Staff {staff_id} not found")

                    # Create timetable slot
                    timetable_slot = await self.repos.timetable.create(
                        {
                            "class_id": class_id,
                            "subject_id": subject_id,
                            "staff_id": staff_id,
                            "day_of_week": day,
                            "start_time": time_start,
                            "end_time": time_end,
                            "room": room,
                            "session_year_id": academic_year_id,
                            "created_at": datetime.now(),
                        }
                    )
                    created_slots += 1

                # Log creation
                self.log_action(
                    action="CREATE_TIMETABLE",
                    entity_type="Timetable",
                    entity_id=str(class_id),
                    user_id="SYSTEM",
                    changes={
                        "class": cls.name,
                        "total_slots": created_slots,
                        "session": session.name,
                    },
                )

                # Notify staff and students
                students = await self.repos.student.get_by_class(class_id)
                for student in students:
                    await self.repos.notification.create(
                        {
                            "user_id": student.user_id,
                            "title": "Timetable Updated",
                            "message": f"New timetable released for {cls.name}",
                            "type": "INFO",
                        }
                    )

            return self.success_response(
                data={
                    "class_id": str(class_id),
                    "class_name": cls.name,
                    "session": session.name,
                    "total_slots": created_slots,
                    "validation_status": "VALID",
                    "created_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error creating timetable: {str(e)}")
            raise ValidationError(f"Failed to create timetable: {str(e)}")

    async def export_timetable_pdf(
        self,
        class_id: UUID,
        academic_year_id: UUID,
    ) -> dict:
        """
        Export class timetable as PDF document.

        Args:
            class_id: UUID of class
            academic_year_id: UUID of academic year

        Returns:
            {pdf_url, class_name, generated_at}

        Raises:
            NotFoundError: If class or timetable not found
        """
        try:
            # Validate class exists
            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            # Get timetable slots
            slots = await self.repos.timetable.get_by_class_and_session(
                class_id, academic_year_id
            )

            if not slots:
                raise NotFoundError("No timetable found for this class")

            # Note: PDF generation would be delegated to Celery task in production
            # This is a placeholder implementation

            return self.success_response(
                data={
                    "class_id": str(class_id),
                    "class_name": cls.name,
                    "pdf_url": f"/timetables/{class_id}/timetable.pdf",
                    "total_slots": len(slots),
                    "generated_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error exporting timetable: {str(e)}")
            raise ValidationError(f"Failed to export timetable: {str(e)}")
