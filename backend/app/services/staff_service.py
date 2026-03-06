"""
Staff Service - Manages staff profiles, assignments, leaves, and performance.

Provides methods for:
- Staff hiring, department transfers, and deactivation
- Subject and class assignments
- Leave request processing and balance tracking
- Substitute teacher assignment
- Staff workload and performance analytics
"""

from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Staff,
    User,
    Leave,
    Subject,
    Class,
    Department,
    SessionYear,
    StudentResult,
    Notification,
)
from app.schemas import StaffResponse, LeaveResponse
from app.utils.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError,
    ConflictError,
)
from app.services.base_service import BaseService
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)

# Contract Type Constants
VALID_CONTRACT_TYPES = {"PERMANENT", "TEMPORARY", "CONTRACT"}

# Leave Type Constants with limits
LEAVE_TYPES = {
    "ANNUAL": {"allowed_days": 21, "requires_approval": True},
    "SICK": {"allowed_days": 10, "requires_approval": False},
    "CASUAL": {"allowed_days": 3, "requires_approval": True},
    "EMERGENCY": {"allowed_days": 5, "requires_approval": True},
    "STUDY_LEAVE": {"allowed_days": float("inf"), "requires_approval": True},
}

# Workload Thresholds (hours per week)
WORKLOAD_THRESHOLDS = {
    "NORMAL": (0, 20),
    "HIGH": (20, 25),
    "CRITICAL": (25, float("inf")),
}


class StaffService(BaseService[Staff]):
    """
    Service for comprehensive staff management and administration.

    Handles staff lifecycle (hiring, assignments, transfers, deactivation),
    leave request processing with balance tracking, and analytics for
    workload and performance evaluation.
    """

    def __init__(self, session: AsyncSession, repos: RepositoryFactory):
        """Initialize StaffService with database session and repositories."""
        super().__init__(Staff, session, repos)
        self.logger = logger

    # ===== STAFF MANAGEMENT METHODS =====

    async def create_staff(
        self,
        user_id: UUID,
        qualification: str,
        specialization: str,
        department_id: UUID,
        phone: str,
        employment_date: date,
        contract_type: str = "PERMANENT",
    ) -> dict:
        """
        Create a new staff member record.

        Args:
            user_id: UUID of user (must have role='STAFF')
            qualification: Staff qualification (min 10 chars)
            specialization: Area of specialization
            department_id: UUID of department
            phone: Contact phone number
            employment_date: Date of employment (past or today)
            contract_type: PERMANENT, TEMPORARY, or CONTRACT

        Returns:
            {staff_id, user_id, name, department, qualification, ...}

        Raises:
            ValidationError: If invalid inputs or user not found
            ConflictError: If staff record already exists for user
        """
        try:
            # Validate user exists and is STAFF role
            user = await self.repos.user.get_by_id(user_id)
            if not user or user.role != "STAFF":
                raise ValidationError(f"User {user_id} not found or not a staff member")

            # Check staff record doesn't already exist
            existing_staff = await self.repos.staff.get_by_user_id(user_id)
            if existing_staff:
                raise ConflictError(f"Staff record already exists for user {user_id}")

            # Validate department exists
            department = await self.repos.department.get_by_id(department_id)
            if not department:
                raise NotFoundError(f"Department {department_id} not found")

            # Validate employment date
            if employment_date > date.today():
                raise ValidationError("Employment date cannot be in the future")

            # Validate qualification
            if not qualification or len(qualification.strip()) < 10:
                raise ValidationError("Qualification must be at least 10 characters")

            # Validate contract type
            if contract_type not in VALID_CONTRACT_TYPES:
                raise ValidationError(
                    f"Invalid contract type: {contract_type}. Must be one of {VALID_CONTRACT_TYPES}"
                )

            # Create staff record
            async with self.transaction():
                staff = await self.repos.staff.create(
                    {
                        "user_id": user_id,
                        "qualification": qualification,
                        "specialization": specialization,
                        "department_id": department_id,
                        "phone": phone,
                        "employment_date": employment_date,
                        "contract_type": contract_type,
                        "is_active": True,
                    }
                )

                # Create audit log
                self.log_action(
                    action="CREATE_STAFF",
                    entity_type="Staff",
                    entity_id=str(staff.id),
                    user_id="SYSTEM",
                    changes={
                        "user_id": str(user_id),
                        "name": f"{user.first_name} {user.last_name}",
                        "department": department.name,
                        "qualification": qualification,
                        "contract_type": contract_type,
                    },
                )

                # Send welcome notification
                await self.repos.notification.create(
                    {
                        "user_id": user_id,
                        "title": "Welcome to Staff System",
                        "message": f"Your staff profile has been created. Department: {department.name}",
                        "type": "INFO",
                    }
                )

            return self.success_response(
                data={
                    "staff_id": str(staff.id),
                    "user_id": str(user_id),
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "phone": phone,
                    "department": department.name,
                    "qualification": qualification,
                    "specialization": specialization,
                    "contract_type": contract_type,
                    "employment_date": str(employment_date),
                    "is_active": True,
                }
            )

        except (ValidationError, ConflictError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Error creating staff: {str(e)}")
            raise ValidationError(f"Failed to create staff: {str(e)}")

    async def assign_staff_to_subject(
        self,
        staff_id: UUID,
        subject_id: UUID,
        class_id: UUID,
        academic_year_id: UUID,
    ) -> dict:
        """
        Assign staff member to teach a subject in a class.

        Args:
            staff_id: UUID of staff member
            subject_id: UUID of subject to teach
            class_id: UUID of class
            academic_year_id: UUID of academic year (must be active)

        Returns:
            {assignment_id, staff_name, subject, class, start_date}

        Raises:
            ValidationError: Qualification mismatch or not found
            ConflictError: Subject already assigned to different staff
        """
        try:
            # Validate all entities exist
            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            subject = await self.repos.subject.get_by_id(subject_id)
            if not subject:
                raise NotFoundError(f"Subject {subject_id} not found")

            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            session = await self.repos.session_year.get_by_id(academic_year_id)
            if not session or not session.is_active:
                raise ValidationError(f"Session {academic_year_id} not active")

            # Check if subject already assigned to different staff in this class
            existing = await self.repos.subject.get_by_class_and_subject(
                class_id, subject_id
            )
            if existing and existing.staff_id != staff_id:
                raise ConflictError(
                    f"Subject already assigned to another staff in this class"
                )

            # Validate qualification match (simple check)
            if subject.required_qualification:
                if subject.required_qualification not in staff.qualification.upper():
                    self.logger.warning(
                        f"Qualification mismatch: {staff.qualification} vs {subject.required_qualification}"
                    )

            async with self.transaction():
                # Create or update subject assignment
                subject_record = await self.repos.subject.create_or_update(
                    {
                        "subject_id": subject_id,
                        "class_id": class_id,
                        "staff_id": staff_id,
                        "session_year_id": academic_year_id,
                        "assigned_date": datetime.now(),
                    }
                )

                # Log assignment
                self.log_action(
                    action="ASSIGN_STAFF_TO_SUBJECT",
                    entity_type="SubjectAssignment",
                    entity_id=str(subject_record.id),
                    user_id="SYSTEM",
                    changes={
                        "staff_id": str(staff_id),
                        "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
                        "subject": subject.name,
                        "class": cls.name,
                        "session": session.name,
                    },
                )

                # Notify staff
                await self.repos.notification.create(
                    {
                        "user_id": staff.user_id,
                        "title": "New Subject Assignment",
                        "message": f"You have been assigned to teach {subject.name} in {cls.name}",
                        "type": "INFO",
                    }
                )

                # Notify admin
                admins = await self.repos.user.get_by_role("ADMIN")
                for admin in admins:
                    await self.repos.notification.create(
                        {
                            "user_id": admin.id,
                            "title": "Staff Assignment Confirmed",
                            "message": f"{staff.user.first_name} assigned to {subject.name} in {cls.name}",
                            "type": "INFO",
                        }
                    )

            return self.success_response(
                data={
                    "assignment_id": str(subject_record.id),
                    "staff_id": str(staff_id),
                    "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
                    "subject": subject.name,
                    "class": cls.name,
                    "session": session.name,
                    "assigned_date": datetime.now().isoformat(),
                }
            )

        except (ValidationError, ConflictError, NotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Error assigning staff to subject: {str(e)}")
            raise ValidationError(f"Failed to assign subject: {str(e)}")

    async def transfer_staff_department(
        self, staff_id: UUID, new_department_id: UUID, reason: str
    ) -> dict:
        """
        Transfer staff member to a different department.

        Args:
            staff_id: UUID of staff to transfer
            new_department_id: UUID of destination department
            reason: Reason for transfer (for audit trail)

        Returns:
            {staff_id, name, old_department, new_department, effective_date}

        Raises:
            NotFoundError: If staff or department not found
            ValidationError: If transfer not allowed
        """
        try:
            # Validate staff exists
            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            old_department = staff.department
            new_department = await self.repos.department.get_by_id(new_department_id)
            if not new_department:
                raise NotFoundError(f"Department {new_department_id} not found")

            if not reason or len(reason.strip()) < 5:
                raise ValidationError("Transfer reason must be at least 5 characters")

            async with self.transaction():
                # Update staff department
                await self.repos.staff.update(
                    staff,
                    {
                        "department_id": new_department_id,
                        "transfer_date": datetime.now(),
                    },
                )

                # Create audit log
                self.log_action(
                    action="TRANSFER_STAFF",
                    entity_type="Staff",
                    entity_id=str(staff_id),
                    user_id="SYSTEM",
                    changes={
                        "from_department": old_department.name,
                        "to_department": new_department.name,
                        "reason": reason,
                        "effective_date": datetime.now().isoformat(),
                    },
                )

                # Notify staff
                await self.repos.notification.create(
                    {
                        "user_id": staff.user_id,
                        "title": "Department Transfer",
                        "message": f"You have been transferred from {old_department.name} to {new_department.name}",
                        "type": "INFO",
                        "data": {"reason": reason},
                    }
                )

            return self.success_response(
                data={
                    "staff_id": str(staff_id),
                    "name": f"{staff.user.first_name} {staff.user.last_name}",
                    "old_department": old_department.name,
                    "new_department": new_department.name,
                    "transfer_date": datetime.now().isoformat(),
                    "reason": reason,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error transferring staff: {str(e)}")
            raise ValidationError(f"Failed to transfer staff: {str(e)}")

    async def update_staff_profile(
        self, staff_id: UUID, updates: dict
    ) -> dict:
        """
        Update staff member profile information.

        Args:
            staff_id: UUID of staff to update
            updates: Dict with keys: qualification, specialization, phone

        Returns:
            {staff_id, updated_fields, changed_at}

        Raises:
            NotFoundError: If staff not found
            ValidationError: If invalid updates
        """
        try:
            # Validate staff exists
            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            # Allowed fields for update
            allowed_fields = {"qualification", "specialization", "phone"}
            provided_fields = set(updates.keys())

            # Check for invalid fields
            invalid_fields = provided_fields - allowed_fields
            if invalid_fields:
                raise ValidationError(
                    f"Cannot update fields: {invalid_fields}. Allowed: {allowed_fields}"
                )

            # Validate data
            if "qualification" in updates:
                qual = updates["qualification"]
                if not qual or len(qual.strip()) < 10:
                    raise ValidationError("Qualification must be at least 10 characters")

            if "phone" in updates:
                phone = updates["phone"]
                if not phone or len(phone.strip()) < 7:
                    raise ValidationError("Invalid phone number")

            # Track changes for audit
            changes = {}
            async with self.transaction():
                for field, value in updates.items():
                    old_value = getattr(staff, field)
                    if old_value != value:
                        changes[field] = {
                            "before": old_value,
                            "after": value,
                        }

                # Update staff
                await self.repos.staff.update(staff, updates)

                # Log changes
                if changes:
                    self.log_action(
                        action="UPDATE_STAFF_PROFILE",
                        entity_type="Staff",
                        entity_id=str(staff_id),
                        user_id="SYSTEM",
                        changes=changes,
                    )

            return self.success_response(
                data={
                    "staff_id": str(staff_id),
                    "updated_fields": list(changes.keys()),
                    "changes": changes,
                    "updated_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error updating staff profile: {str(e)}")
            raise ValidationError(f"Failed to update staff: {str(e)}")

    async def deactivate_staff(
        self, staff_id: UUID, reason: str, effective_date: date
    ) -> dict:
        """
        Deactivate a staff member (soft delete).

        Args:
            staff_id: UUID of staff to deactivate
            reason: Reason for deactivation
            effective_date: Date deactivation becomes effective

        Returns:
            {staff_id, name, deactivation_date, reason}

        Raises:
            NotFoundError: If staff not found
            ValidationError: If invalid date or reason
        """
        try:
            # Validate staff exists
            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            # Validate effective date
            if effective_date < date.today():
                raise ValidationError("Effective date must be today or in future")

            if not reason or len(reason.strip()) < 5:
                raise ValidationError("Deactivation reason must be at least 5 characters")

            async with self.transaction():
                # Deactivate staff
                await self.repos.staff.update(
                    staff,
                    {
                        "is_active": False,
                        "deactivation_date": effective_date,
                        "deactivation_reason": reason,
                    },
                )

                # Create audit log
                self.log_action(
                    action="DEACTIVATE_STAFF",
                    entity_type="Staff",
                    entity_id=str(staff_id),
                    user_id="SYSTEM",
                    changes={
                        "is_active": False,
                        "reason": reason,
                        "effective_date": str(effective_date),
                    },
                )

                # Notify staff
                await self.repos.notification.create(
                    {
                        "user_id": staff.user_id,
                        "title": "Staff Deactivation",
                        "message": f"Your staff account will be deactivated on {effective_date}",
                        "type": "WARNING",
                        "data": {"reason": reason},
                    }
                )

            return self.success_response(
                data={
                    "staff_id": str(staff_id),
                    "name": f"{staff.user.first_name} {staff.user.last_name}",
                    "deactivation_date": str(effective_date),
                    "reason": reason,
                    "is_active": False,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error deactivating staff: {str(e)}")
            raise ValidationError(f"Failed to deactivate staff: {str(e)}")

    # ===== LEAVE PROCESSING METHODS =====

    async def process_staff_leave_request(
        self,
        leave_id: UUID,
        action: str,
        admin_id: UUID,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Approve or reject a staff leave request.

        Args:
            leave_id: UUID of leave request
            action: "APPROVE" or "REJECT"
            admin_id: UUID of admin processing request
            notes: Optional notes on decision

        Returns:
            {leave_id, status, approved_by, approved_date}

        Raises:
            NotFoundError: If leave or admin not found
            ValidationError: If invalid action or balance exceeded
        """
        try:
            # Validate leave exists
            leave = await self.repos.leave.get_by_id(leave_id)
            if not leave:
                raise NotFoundError(f"Leave request {leave_id} not found")

            if leave.status != "PENDING":
                raise ConflictError(
                    f"Leave request is already {leave.status}"
                )

            # Validate admin exists
            admin = await self.repos.user.get_by_id(admin_id)
            if not admin or admin.role != "ADMIN":
                raise ForbiddenError("Only admins can process leave requests")

            if action not in ["APPROVE", "REJECT"]:
                raise ValidationError(f"Invalid action: {action}. Must be APPROVE or REJECT")

            async with self.transaction():
                if action == "APPROVE":
                    # Check leave balance
                    balance = await self.get_staff_leave_balance(
                        leave.staff_id, leave.session_year_id
                    )
                    leave_type_balance = None
                    for lt_bal in balance.get("leaves", []):
                        if lt_bal["leave_type"] == leave.leave_type:
                            leave_type_balance = lt_bal
                            break

                    if leave_type_balance and leave_type_balance["remaining"] < (leave.end_date - leave.start_date).days + 1:
                        raise ValidationError(
                            f"Insufficient {leave.leave_type} leave balance"
                        )

                    # Update leave status
                    await self.repos.leave.update(
                        leave,
                        {
                            "status": "APPROVED",
                            "approved_by": admin_id,
                            "approved_date": datetime.now(),
                            "approval_notes": notes,
                        },
                    )

                    # Notify staff
                    await self.repos.notification.create(
                        {
                            "user_id": leave.staff_id,
                            "title": "Leave Approved",
                            "message": f"Your {leave.leave_type} leave from {leave.start_date} to {leave.end_date} has been approved",
                            "type": "INFO",
                        }
                    )

                else:  # REJECT
                    await self.repos.leave.update(
                        leave,
                        {
                            "status": "REJECTED",
                            "rejected_by": admin_id,
                            "rejected_date": datetime.now(),
                            "rejection_reason": notes,
                        },
                    )

                    # Notify staff
                    await self.repos.notification.create(
                        {
                            "user_id": leave.staff_id,
                            "title": "Leave Rejected",
                            "message": f"Your {leave.leave_type} leave request has been rejected. Reason: {notes}",
                            "type": "WARNING",
                        }
                    )

                # Log action
                self.log_action(
                    action=f"LEAVE_REQUEST_{action}",
                    entity_type="Leave",
                    entity_id=str(leave_id),
                    user_id=str(admin_id),
                    changes={
                        "status": action,
                        "notes": notes,
                        "leave_type": leave.leave_type,
                        "duration_days": (leave.end_date - leave.start_date).days + 1,
                    },
                )

            return self.success_response(
                data={
                    "leave_id": str(leave_id),
                    "status": action,
                    "approved_by": str(admin_id),
                    "processed_date": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError, ForbiddenError, ConflictError):
            raise
        except Exception as e:
            self.logger.error(f"Error processing leave request: {str(e)}")
            raise ValidationError(f"Failed to process leave request: {str(e)}")

    async def get_staff_leave_balance(
        self,
        staff_id: UUID,
        academic_year_id: Optional[UUID] = None,
    ) -> dict:
        """
        Get leave balance for staff member by type.

        Args:
            staff_id: UUID of staff
            academic_year_id: Optional (uses current if not provided)

        Returns:
            {
                staff_id,
                session,
                leaves: [{leave_type, allowed, used, remaining, pending}]
            }

        Raises:
            NotFoundError: If staff or session not found
        """
        try:
            # Validate staff exists
            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            # Get current session if not provided
            if not academic_year_id:
                session = await self.repos.session_year.get_current()
                if not session:
                    raise NotFoundError("No active session year")
                academic_year_id = session.id
            else:
                session = await self.repos.session_year.get_by_id(academic_year_id)
                if not session:
                    raise NotFoundError(f"Session {academic_year_id} not found")

            # Get all leaves for staff in this session
            leaves = await self.repos.leave.get_by_staff_and_session(
                staff_id, academic_year_id
            )

            # Calculate balance by type
            leave_balances = []
            for leave_type, config in LEAVE_TYPES.items():
                allowed = int(config["allowed_days"]) if config["allowed_days"] != float("inf") else 999
                type_leaves = [l for l in leaves if l.leave_type == leave_type]

                # Count used days (approved only)
                approved_leaves = [l for l in type_leaves if l.status == "APPROVED"]
                used = sum(
                    (l.end_date - l.start_date).days + 1
                    for l in approved_leaves
                )

                # Count pending days
                pending_leaves = [l for l in type_leaves if l.status == "PENDING"]
                pending = sum(
                    (l.end_date - l.start_date).days + 1
                    for l in pending_leaves
                )

                remaining = allowed - used
                leave_balances.append(
                    {
                        "leave_type": leave_type,
                        "allowed": allowed,
                        "used": used,
                        "remaining": max(remaining, 0),
                        "pending": pending,
                    }
                )

            return self.success_response(
                data={
                    "staff_id": str(staff_id),
                    "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
                    "session": session.name,
                    "leaves": leave_balances,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error getting leave balance: {str(e)}")
            raise ValidationError(f"Failed to get leave balance: {str(e)}")

    async def assign_substitute_teacher(
        self, leave_id: UUID, substitute_staff_id: UUID
    ) -> dict:
        """
        Assign a substitute teacher for an approved leave period.

        Args:
            leave_id: UUID of approved leave request
            substitute_staff_id: UUID of substitute staff member

        Returns:
            {assignment_id, original_staff, substitute, start_date, end_date}

        Raises:
            NotFoundError: If leave or substitute not found
            ValidationError: If leave not approved or conflicts exist
        """
        try:
            # Validate leave exists and is approved
            leave = await self.repos.leave.get_by_id(leave_id)
            if not leave:
                raise NotFoundError(f"Leave request {leave_id} not found")

            if leave.status != "APPROVED":
                raise ValidationError("Only approved leaves can have substitutes")

            # Validate substitute staff
            substitute = await self.repos.staff.get_by_id(substitute_staff_id)
            if not substitute or not substitute.is_active:
                raise ValidationError(f"Substitute staff {substitute_staff_id} not active")

            # Check substitute doesn't exceed consecutive limit (15 days)
            duration = (leave.end_date - leave.start_date).days + 1
            if duration > 15:
                raise ValidationError("Substitute cannot cover more than 15 consecutive days")

            async with self.transaction():
                # Create temporary assignment record
                assignment = await self.repos.subject.create(
                    {
                        "staff_id": substitute_staff_id,
                        "original_staff_id": leave.staff_id,
                        "start_date": leave.start_date,
                        "end_date": leave.end_date,
                        "assignment_type": "SUBSTITUTE",
                        "session_year_id": leave.session_year_id,
                    }
                )

                # Log assignment
                self.log_action(
                    action="ASSIGN_SUBSTITUTE",
                    entity_type="SubstituteAssignment",
                    entity_id=str(assignment.id),
                    user_id="SYSTEM",
                    changes={
                        "leave_id": str(leave_id),
                        "original_staff": leave.staff.user.first_name + " " + leave.staff.user.last_name,
                        "substitute": substitute.user.first_name + " " + substitute.user.last_name,
                        "duration_days": duration,
                    },
                )

                # Notify substitute
                await self.repos.notification.create(
                    {
                        "user_id": substitute.user_id,
                        "title": "Substitute Assignment",
                        "message": f"You are assigned as substitute from {leave.start_date} to {leave.end_date}",
                        "type": "INFO",
                    }
                )

            return self.success_response(
                data={
                    "assignment_id": str(assignment.id),
                    "leave_id": str(leave_id),
                    "original_staff": f"{leave.staff.user.first_name} {leave.staff.user.last_name}",
                    "substitute": f"{substitute.user.first_name} {substitute.user.last_name}",
                    "start_date": str(leave.start_date),
                    "end_date": str(leave.end_date),
                    "duration_days": duration,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error assigning substitute: {str(e)}")
            raise ValidationError(f"Failed to assign substitute: {str(e)}")

    # ===== ANALYTICS METHODS =====

    async def get_staff_workload(
        self,
        staff_id: UUID,
        academic_year_id: Optional[UUID] = None,
    ) -> dict:
        """
        Calculate staff member's workload metrics.

        Args:
            staff_id: UUID of staff
            academic_year_id: Optional (uses current if not provided)

        Returns:
            {
                staff_id,
                session,
                subjects: [{subject, class_size, hours_per_week, pending_work}],
                total_hours: float,
                workload_status: "NORMAL" | "HIGH" | "CRITICAL"
            }

        Raises:
            NotFoundError: If staff not found
        """
        try:
            # Validate staff
            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            # Get current session if not provided
            if not academic_year_id:
                session = await self.repos.session_year.get_current()
                if not session:
                    raise NotFoundError("No active session year")
                academic_year_id = session.id
            else:
                session = await self.repos.session_year.get_by_id(academic_year_id)

            # Get all subjects assigned to staff
            assignments = await self.repos.subject.get_by_staff_and_session(
                staff_id, academic_year_id
            )

            subjects_workload = []
            total_hours = 0.0

            for assignment in assignments:
                # Count students in class
                students = await self.repos.student.get_by_class(assignment.class_id)
                class_size = len(students) if students else 0

                # Hours per week (assume 1 hour per class, frequency varies)
                hours_per_week = 3.0  # Default, could be configurable

                # Count pending work
                pending_submissions = await self.repos.assignment_submission.get_pending_by_staff(
                    staff_id, assignment.subject_id
                )
                pending_count = len(pending_submissions) if pending_submissions else 0

                subjects_workload.append(
                    {
                        "subject": assignment.subject.name,
                        "class": assignment.class_.name,
                        "students": class_size,
                        "hours_per_week": hours_per_week,
                        "pending_grading": pending_count,
                    }
                )

                total_hours += hours_per_week

            # Determine workload status
            workload_status = "NORMAL"
            for status, (min_h, max_h) in WORKLOAD_THRESHOLDS.items():
                if min_h <= total_hours < max_h:
                    workload_status = status
                    break

            return self.success_response(
                data={
                    "staff_id": str(staff_id),
                    "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
                    "session": session.name,
                    "subjects": subjects_workload,
                    "total_hours_per_week": round(total_hours, 2),
                    "workload_status": workload_status,
                    "assignment_count": len(assignments),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error calculating workload: {str(e)}")
            raise ValidationError(f"Failed to calculate workload: {str(e)}")

    async def get_staff_performance(
        self,
        staff_id: UUID,
        academic_year_id: Optional[UUID] = None,
    ) -> dict:
        """
        Calculate staff member's performance metrics.

        Args:
            staff_id: UUID of staff
            academic_year_id: Optional (uses current if not provided)

        Returns:
            {
                staff_id,
                overall_rating,
                student_feedback,
                quiz_performance,
                assignment_submission_rate,
                grading_speed_days,
                attendance_rate
            }

        Raises:
            NotFoundError: If staff not found
        """
        try:
            # Validate staff
            staff = await self.repos.staff.get_by_id(staff_id)
            if not staff:
                raise NotFoundError(f"Staff {staff_id} not found")

            # Get current session
            if not academic_year_id:
                session = await self.repos.session_year.get_current()
                if not session:
                    raise NotFoundError("No active session year")
                academic_year_id = session.id

            # Get all results graded by this staff
            results = await self.repos.student_result.get_by_grading_staff(
                staff_id, academic_year_id
            )

            # Calculate metrics
            if results:
                avg_quiz_score = sum(r.score for r in results if r.score) / len(
                    [r for r in results if r.score]
                )
            else:
                avg_quiz_score = 0.0

            # Get staff attendance
            attendance_records = await self.repos.attendance_report.get_by_staff(
                staff_id, academic_year_id
            )
            if attendance_records:
                present_count = sum(
                    1 for r in attendance_records if r.status == "PRESENT"
                )
                attendance_rate = (present_count / len(attendance_records)) * 100
            else:
                attendance_rate = 0.0

            # Overall rating (composite)
            overall_rating = min(
                5.0,
                (avg_quiz_score / 100) * 5 * 0.5
                + (attendance_rate / 100) * 5 * 0.5,
            )

            return self.success_response(
                data={
                    "staff_id": str(staff_id),
                    "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
                    "overall_rating": round(overall_rating, 2),
                    "quiz_performance": round(avg_quiz_score, 2),
                    "attendance_rate": round(attendance_rate, 2),
                    "grading_speed_days": 2.5,  # Placeholder
                    "session": (await self.repos.session_year.get_by_id(academic_year_id)).name,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error calculating performance: {str(e)}")
            raise ValidationError(f"Failed to calculate performance: {str(e)}")
