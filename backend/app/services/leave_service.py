"""
Leave Service - Leave request management and approval workflow.

Provides:
- Leave request submission with type validation
- Leave balance tracking per session year
- Approval/rejection workflow
- Chronic absence detection
- Notification on status changes
"""

from datetime import datetime, date as date_type, timedelta
from typing import Optional, List
from uuid import UUID

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
)
from app.models.leave import LeaveReport
from app.repositories.factory import RepositoryFactory
from app.schemas.leave import LeaveResponse, LeaveBalanceSchema
from app.services.base import BaseService


# Leave type constants
LEAVE_TYPES = {
    "ANNUAL": {"allowed_days": 21, "requires_approval": True},
    "CASUAL": {"allowed_days": 5, "requires_approval": True},
    "SICK": {"allowed_days": 10, "requires_approval": False},
    "EMERGENCY": {"allowed_days": 3, "requires_approval": True},
}


class LeaveService(BaseService[LeaveReport]):
    """
    Leave service for managing leave requests and approvals.
    
    Handles:
    - Leave request submission with validation
    - Leave balance tracking per session year
    - Approval and rejection workflow
    - Chronic absence detection and warnings
    - Comprehensive audit logging
    
    Usage:
        leave_service = LeaveService(repos)
        
        # Request leave
        leave = await leave_service.request_leave(
            user_id=user_id,
            start_date=date(2024, 3, 10),
            end_date=date(2024, 3, 12),
            reason="Family emergency",
            leave_type="EMERGENCY"
        )
        
        # Get leave balance
        balance = await leave_service.get_leave_balance(
            user_id=user_id,
            session_year_id=session_year_id
        )
        
        # Approve leave
        result = await leave_service.approve_leave(
            leave_id=leave_id,
            admin_id=admin_id,
            approval_notes="Approved by principal"
        )
    """

    async def request_leave(
        self,
        user_id: UUID,
        start_date: date_type,
        end_date: date_type,
        reason: str,
        leave_type: str,
    ) -> dict:
        """
        Submit a leave request.
        
        Validates user, dates, and leave type. Checks leave balance for applicable
        types. Creates LeaveReport record with PENDING status and notifies admins.
        
        Args:
            user_id: ID of user requesting leave
            start_date: Start date of leave (must be >= today)
            end_date: End date of leave (must be > start_date)
            reason: Reason for leave (e.g., "Family emergency")
            leave_type: Type of leave: "ANNUAL", "CASUAL", "SICK", "EMERGENCY"
        
        Returns:
            Success response with LeaveResponse (status=PENDING)
        
        Raises:
            NotFoundError: If user not found
            ValidationError: If dates invalid, leave_type invalid, or insufficient balance
        
        Example:
            result = await leave_service.request_leave(
                user_id=user_id,
                start_date=date(2024, 3, 15),
                end_date=date(2024, 3, 17),
                reason="Annual vacation",
                leave_type="ANNUAL"
            )
        """
        # Validate user exists
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")

        # Validate leave_type
        if leave_type not in LEAVE_TYPES:
            raise ValidationError(
                f"Invalid leave type. Must be one of: {', '.join(LEAVE_TYPES.keys())}"
            )

        # Validate dates
        today = date_type.today()
        if start_date < today:
            raise ValidationError("Start date must be today or in the future")
        if end_date <= start_date:
            raise ValidationError("End date must be after start date")

        # Validate reason
        self._validate_field_length(reason, "reason", min_len=5, max_len=500)

        # Check leave balance for balance-limited types
        if leave_type in ["ANNUAL", "CASUAL"]:
            # Get current session year
            session_year = await self.repos.session_year.get_current_session()
            if session_year:
                balance_info = await self.get_leave_balance(
                    user_id, session_year.id
                )
                remaining = balance_info["data"]["remaining"]
                requested_days = (end_date - start_date).days + 1
                if remaining < requested_days:
                    raise ValidationError(
                        f"Insufficient leave balance. Remaining: {remaining} days, "
                        f"Requested: {requested_days} days"
                    )

        try:
            async with self.transaction():
                # Create leave request
                leave_record = await self.repos.leave_report.create({
                    "user_id": user_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "reason": reason,
                    "leave_type": leave_type,
                    "status": "PENDING",
                    "requested_at": datetime.utcnow(),
                })

                # Notify admins
                admins = await self.repos.user.get_by_role("ADMIN")
                for admin in admins:
                    days = (end_date - start_date).days + 1
                    await self.repos.notification.create({
                        "user_id": admin.id,
                        "title": f"Leave Request: {user.first_name} {user.last_name}",
                        "message": (
                            f"{user.first_name} {user.last_name} requested {days} days "
                            f"of {leave_type} leave from {start_date} to {end_date}. "
                            f"Reason: {reason}"
                        ),
                        "type": "LEAVE_REQUEST",
                        "priority": "MEDIUM",
                        "is_read": False,
                    })

                # Audit log
                days = (end_date - start_date).days + 1
                self.log_audit(
                    action="REQUEST_LEAVE",
                    entity="LeaveReport",
                    entity_id=leave_record.id,
                    user_id=user_id,
                    changes={
                        "leave_type": leave_type,
                        "days": days,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                )
                self.logger.info(
                    f"User {user_id} requested {days} days of {leave_type} leave"
                )

                return self.success_response(
                    message="Leave request submitted successfully",
                    data={
                        "leave_id": str(leave_record.id),
                        "user_id": str(user_id),
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "leave_type": leave_type,
                        "status": "PENDING",
                        "requested_at": datetime.utcnow().isoformat(),
                    },
                )

        except Exception as e:
            self.logger.error(f"Request leave error: {str(e)}")
            raise

    async def get_leave_balance(
        self,
        user_id: UUID,
        session_year_id: UUID,
    ) -> dict:
        """
        Get leave balance for a user in a session year.
        
        Calculates total allowed days, used days, and remaining balance
        based on approved leave requests for the session.
        
        Args:
            user_id: ID of user
            session_year_id: ID of session year
        
        Returns:
            Success response with LeaveBalanceSchema containing:
            - leave_type: Type of leave (ANNUAL, CASUAL, etc.)
            - total_allowed: Total days allowed for this type
            - used: Days already used
            - remaining: Days left
        
        Raises:
            NotFoundError: If user or session year not found
        
        Example:
            result = await leave_service.get_leave_balance(
                user_id=user_id,
                session_year_id=session_year_id
            )
            if result["success"]:
                for balance in result["data"]:
                    print(f"{balance['leave_type']}: {balance['remaining']} days left")
        """
        # Validate user and session year exist
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")

        session_year = await self.repos.session_year.get_by_id(session_year_id)
        if not session_year:
            raise NotFoundError(f"Session year #{session_year_id} not found")

        try:
            # Fetch all approved leaves for user in this session
            all_leaves = await self.repos.leave_report.get_by_user_and_session(
                user_id, session_year_id
            )
            approved_leaves = [
                l for l in all_leaves if l.status == "APPROVED"
            ]

            # Calculate balance for each leave type
            balances = []
            for leave_type, config in LEAVE_TYPES.items():
                # Get leaves of this type
                type_leaves = [
                    l for l in approved_leaves if l.leave_type == leave_type
                ]

                # Calculate used days
                used_days = sum(
                    (l.end_date - l.start_date).days + 1 for l in type_leaves
                )

                # Calculate remaining
                total_allowed = config["allowed_days"]
                remaining = total_allowed - used_days

                balances.append({
                    "leave_type": leave_type,
                    "total_allowed": total_allowed,
                    "used": used_days,
                    "remaining": max(0, remaining),
                })

            self.logger.debug(
                f"Leave balance calculated for user {user_id} in session {session_year_id}"
            )

            return self.success_response(
                message="Leave balance retrieved successfully",
                data=balances,
            )

        except Exception as e:
            self.logger.error(f"Get leave balance error: {str(e)}")
            raise

    async def approve_leave(
        self,
        leave_id: UUID,
        admin_id: UUID,
        approval_notes: Optional[str] = None,
    ) -> dict:
        """
        Approve a pending leave request.
        
        Updates leave status to APPROVED, records approver and notes,
        and sends notification to user.
        
        Args:
            leave_id: ID of leave request to approve
            admin_id: ID of admin approving (authorization in endpoint)
            approval_notes: Optional notes from approver
        
        Returns:
            Success response with updated LeaveResponse (status=APPROVED)
        
        Raises:
            NotFoundError: If leave request not found
            ValidationError: If leave not PENDING
        
        Example:
            result = await leave_service.approve_leave(
                leave_id=leave_id,
                admin_id=admin_id,
                approval_notes="Approved by principal"
            )
        """
        # Validate leave exists
        leave = await self.repos.leave_report.get_by_id(leave_id)
        if not leave:
            raise NotFoundError(f"Leave request #{leave_id} not found")

        if leave.status != "PENDING":
            raise ValidationError(
                f"Cannot approve: leave is {leave.status}"
            )

        if approval_notes:
            self._validate_field_length(
                approval_notes, "approval_notes", min_len=1, max_len=500
            )

        try:
            async with self.transaction():
                # Update leave
                approved_leave = await self.repos.leave_report.update(
                    leave,
                    {
                        "status": "APPROVED",
                        "approved_at": datetime.utcnow(),
                        "approved_by": admin_id,
                        "approval_notes": approval_notes,
                    },
                )

                # Get user for notification
                user = await self.repos.user.get_by_id(leave.user_id)

                # Notify user
                if user:
                    days = (leave.end_date - leave.start_date).days + 1
                    await self.repos.notification.create({
                        "user_id": user.id,
                        "title": "Leave Request Approved",
                        "message": (
                            f"Your leave request ({leave.leave_type}) from "
                            f"{leave.start_date} to {leave.end_date} has been approved. "
                            f"({days} days)"
                        ),
                        "type": "LEAVE_APPROVED",
                        "priority": "HIGH",
                        "is_read": False,
                    })

                # Audit log
                self.log_audit(
                    action="APPROVE_LEAVE",
                    entity="LeaveReport",
                    entity_id=leave_id,
                    user_id=admin_id,
                    changes={"status": "APPROVED"},
                )
                self.logger.info(f"Leave request {leave_id} approved by {admin_id}")

                return self.success_response(
                    message="Leave request approved successfully",
                    data={
                        "leave_id": str(leave_id),
                        "user_id": str(leave.user_id),
                        "status": "APPROVED",
                        "approved_at": datetime.utcnow().isoformat(),
                    },
                )

        except Exception as e:
            self.logger.error(f"Approve leave error: {str(e)}")
            raise

    async def reject_leave(
        self,
        leave_id: UUID,
        admin_id: UUID,
        rejection_reason: str,
    ) -> dict:
        """
        Reject a pending leave request.
        
        Updates leave status to REJECTED with reason and notifies user.
        
        Args:
            leave_id: ID of leave request to reject
            admin_id: ID of admin rejecting (authorization in endpoint)
            rejection_reason: Reason for rejection
        
        Returns:
            Success response with updated LeaveResponse (status=REJECTED)
        
        Raises:
            NotFoundError: If leave request not found
            ValidationError: If leave not PENDING or reason invalid
        
        Example:
            result = await leave_service.reject_leave(
                leave_id=leave_id,
                admin_id=admin_id,
                rejection_reason="Insufficient leave balance"
            )
        """
        # Validate leave exists
        leave = await self.repos.leave_report.get_by_id(leave_id)
        if not leave:
            raise NotFoundError(f"Leave request #{leave_id} not found")

        if leave.status != "PENDING":
            raise ValidationError(f"Cannot reject: leave is {leave.status}")

        # Validate reason
        self._validate_field_length(
            rejection_reason, "rejection_reason", min_len=5, max_len=500
        )

        try:
            async with self.transaction():
                # Update leave
                rejected_leave = await self.repos.leave_report.update(
                    leave,
                    {
                        "status": "REJECTED",
                        "rejected_at": datetime.utcnow(),
                        "rejected_by": admin_id,
                        "rejection_reason": rejection_reason,
                    },
                )

                # Get user for notification
                user = await self.repos.user.get_by_id(leave.user_id)

                # Notify user
                if user:
                    await self.repos.notification.create({
                        "user_id": user.id,
                        "title": "Leave Request Rejected",
                        "message": (
                            f"Your leave request ({leave.leave_type}) from "
                            f"{leave.start_date} to {leave.end_date} has been rejected. "
                            f"Reason: {rejection_reason}"
                        ),
                        "type": "LEAVE_REJECTED",
                        "priority": "HIGH",
                        "is_read": False,
                    })

                # Audit log
                self.log_audit(
                    action="REJECT_LEAVE",
                    entity="LeaveReport",
                    entity_id=leave_id,
                    user_id=admin_id,
                    changes={
                        "status": "REJECTED",
                        "reason": rejection_reason,
                    },
                )
                self.logger.info(f"Leave request {leave_id} rejected by {admin_id}")

                return self.success_response(
                    message="Leave request rejected successfully",
                    data={
                        "leave_id": str(leave_id),
                        "user_id": str(leave.user_id),
                        "status": "REJECTED",
                        "rejected_at": datetime.utcnow().isoformat(),
                    },
                )

        except Exception as e:
            self.logger.error(f"Reject leave error: {str(e)}")
            raise

    async def get_pending_leaves(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """
        Get all pending leave requests (admin only).
        
        Returns paginated list of pending leave requests for admin review.
        
        Args:
            skip: Pagination skip (default 0)
            limit: Pagination limit (default 20, max 100)
        
        Returns:
            Success response with data containing:
            - leaves: List of pending leave requests
            - total: Total pending count
            - skip, limit: Pagination parameters
        
        Example:
            result = await leave_service.get_pending_leaves(skip=0, limit=50)
            for leave in result["data"]["leaves"]:
                print(f"{leave['user_name']}: {leave['leave_type']}")
        """
        # Validate pagination
        limit = min(limit, 100)
        if skip < 0:
            skip = 0

        try:
            # Fetch pending leaves with pagination
            leaves, total = (
                await self.repos.leave_report.get_pending_paginated(
                    skip=skip, limit=limit
                )
            )

            # Build leave details
            leave_details = []
            for leave in leaves:
                user = await self.repos.user.get_by_id(leave.user_id)
                user_name = (
                    f"{user.first_name} {user.last_name}" if user else "Unknown"
                )
                days = (leave.end_date - leave.start_date).days + 1

                leave_details.append({
                    "leave_id": str(leave.id),
                    "user_id": str(leave.user_id),
                    "user_name": user_name,
                    "leave_type": leave.leave_type,
                    "start_date": leave.start_date.isoformat(),
                    "end_date": leave.end_date.isoformat(),
                    "days": days,
                    "reason": leave.reason,
                    "requested_at": (
                        leave.requested_at.isoformat()
                        if leave.requested_at
                        else None
                    ),
                })

            self.logger.info(f"Retrieved {len(leaves)} pending leave requests")

            return self.success_response(
                message="Pending leave requests retrieved successfully",
                data={
                    "leaves": leave_details,
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                },
            )

        except Exception as e:
            self.logger.error(f"Get pending leaves error: {str(e)}")
            raise

    async def mark_chronic_absence(
        self,
        user_id: UUID,
        session_year_id: UUID,
        threshold: int = 20,
    ) -> dict:
        """
        Mark user with chronic absence if attendance below threshold.
        
        Calculates attendance rate for user in session. If below threshold
        percentage, creates warning and notifies user and admins.
        
        Args:
            user_id: ID of user
            session_year_id: ID of session year
            threshold: Absence threshold percentage (default 20%)
        
        Returns:
            Dictionary containing:
            - user_id: User ID
            - attendance_rate: Calculated percentage
            - status: "WARNED" if below threshold, "OK" otherwise
        
        Raises:
            NotFoundError: If user or session year not found
        
        Example:
            result = await leave_service.mark_chronic_absence(
                user_id=user_id,
                session_year_id=session_year_id,
                threshold=15  # 15% absent = chronic
            )
        """
        # Validate user and session year
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")

        session_year = await self.repos.session_year.get_by_id(session_year_id)
        if not session_year:
            raise NotFoundError(f"Session year #{session_year_id} not found")

        try:
            # Calculate attendance rate (would use AttendanceRepository)
            attendance_rate = await self._calculate_attendance_rate(
                user_id, session_year_id
            )

            absence_rate = 100 - attendance_rate
            is_chronic = absence_rate > threshold

            if is_chronic:
                # Create warning notification
                await self.repos.notification.create({
                    "user_id": user_id,
                    "title": "Chronic Absence Warning",
                    "message": (
                        f"Your absence rate ({absence_rate:.1f}%) exceeds the threshold "
                        f"({threshold}%). Please contact your administrator."
                    ),
                    "type": "CHRONIC_ABSENCE",
                    "priority": "CRITICAL",
                    "is_read": False,
                })

                # Notify admins
                admins = await self.repos.user.get_by_role("ADMIN")
                for admin in admins:
                    await self.repos.notification.create({
                        "user_id": admin.id,
                        "title": f"Chronic Absence: {user.first_name} {user.last_name}",
                        "message": (
                            f"User {user.first_name} {user.last_name} has chronic absence "
                            f"({absence_rate:.1f}% absent) in current session."
                        ),
                        "type": "CHRONIC_ABSENCE",
                        "priority": "HIGH",
                        "is_read": False,
                    })

                # Audit log
                self.log_audit(
                    action="MARK_CHRONIC_ABSENCE",
                    entity="User",
                    entity_id=user_id,
                    changes={"absence_rate": absence_rate},
                )
                self.logger.warning(
                    f"User {user_id} marked with chronic absence ({absence_rate}%)"
                )

            self.logger.info(
                f"Attendance check for {user_id}: {attendance_rate}% present"
            )

            return self.success_response(
                message="Chronic absence check completed",
                data={
                    "user_id": str(user_id),
                    "attendance_rate": round(attendance_rate, 1),
                    "absence_rate": round(absence_rate, 1),
                    "threshold": threshold,
                    "status": "WARNED" if is_chronic else "OK",
                },
            )

        except Exception as e:
            self.logger.error(f"Mark chronic absence error: {str(e)}")
            raise

    async def _calculate_attendance_rate(
        self,
        user_id: UUID,
        session_year_id: UUID,
    ) -> float:
        """
        Calculate attendance rate for a user in a session.
        
        Args:
            user_id: ID of user
            session_year_id: ID of session year
        
        Returns:
            Attendance percentage (0-100)
        """
        # TODO: Fetch attendance records and calculate
        # Would use AttendanceRepository to get attendance data
        # For now, return placeholder
        return 75.0
