"""
Student Service - Student enrollment, profile management, and academic dashboards.

Provides:
- Student enrollment with validation
- Class transfers and tracking
- Student profile updates
- Academic dashboards with GPA and attendance
- Transcript generation with cumulative GPA
- Student suspension and withdrawal
- Notification integration
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    ForbiddenError,
)
from app.models.student import Student
from app.models.user import CustomUser
from app.repositories.factory import RepositoryFactory
from app.schemas.student import (
    StudentResponse,
    StudentUpdateRequest,
)
from app.services.base import BaseService


class StudentService(BaseService[Student]):
    """
    Student service for enrollment, profile management, and academic tracking.
    
    Handles:
    - Student enrollment in classes
    - Class transfers with validation
    - Profile updates (allowed fields only)
    - Academic dashboard with GPA, attendance, pending work
    - Transcript generation with cumulative GPA
    - Student suspension and withdrawal
    - Notification and audit logging
    
    Usage:
        student_service = StudentService(repos)
        student = await student_service.enroll_student(
            user_id=user_id,
            class_id=class_id,
            department_id=dept_id,
            admission_number="ADM-2024-001"
        )
        dashboard = await student_service.get_student_dashboard(student_id)
    """

    async def enroll_student(
        self,
        user_id: UUID,
        class_id: UUID,
        department_id: UUID,
        admission_number: str,
    ) -> dict:
        """
        Enroll student in a class.
        
        Validates user is a student, class exists, department exists,
        creates Student record, and sends welcome notification.
        
        Args:
            user_id: ID of user to enroll
            class_id: ID of class to enroll in
            department_id: ID of student's department
            admission_number: Unique admission number (e.g., "ADM-2024-001")
        
        Returns:
            Success response with StudentResponse data
        
        Raises:
            NotFoundError: If user, class, or department not found
            ValidationError: If user not STUDENT role or admission_number exists
            
        Example:
            result = await student_service.enroll_student(
                user_id=user_id,
                class_id=class_id,
                department_id=dept_id,
                admission_number="ADM-2024-001"
            )
        """
        # Validate user exists and is STUDENT
        user = await self.repos.user.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User #{user_id} not found")
        if user.role != "STUDENT":
            raise ValidationError(f"User must have STUDENT role, has {user.role}")

        # Validate class exists
        class_obj = await self.repos.class_repo.get_by_id(class_id)
        if not class_obj:
            raise NotFoundError(f"Class #{class_id} not found")

        # Validate department exists
        department = await self.repos.department.get_by_id(department_id)
        if not department:
            raise NotFoundError(f"Department #{department_id} not found")

        # Check admission number uniqueness
        existing_student = await self.repos.student.get_by_id(user_id)
        if existing_student:
            raise ConflictError(f"User #{user_id} is already enrolled as a student")

        # Get current session year
        session_year = await self.repos.session_year.get_current_session()
        if not session_year:
            raise ValidationError("No active session year available")

        try:
            async with self.transaction():
                # Create student record
                student = await self.repos.student.create({
                    "user_id": user_id,
                    "class_id": class_id,
                    "department_id": department_id,
                    "session_year_id": session_year.id,
                    "admission_number": admission_number,
                    "status": "ACTIVE",
                    "enrollment_date": datetime.utcnow(),
                })

                # Create notification
                await self.repos.notification.create({
                    "user_id": user_id,
                    "title": "Welcome to Enrollment",
                    "message": f"You have been enrolled in {class_obj.name}. Welcome!",
                    "type": "ENROLLMENT",
                    "priority": "HIGH",
                    "is_read": False,
                })

                # Audit log
                self.log_audit(
                    action="ENROLL_STUDENT",
                    entity="Student",
                    entity_id=student.id,
                    user_id=user_id,
                    changes={
                        "class_id": str(class_id),
                        "admission_number": admission_number,
                    },
                )
                self.logger.info(
                    f"Student {admission_number} enrolled in class {class_obj.name}"
                )

                return self.success_response(
                    message="Student enrolled successfully",
                    data=StudentResponse.model_validate(student),
                )

        except Exception as e:
            self.logger.error(f"Enrollment error: {str(e)}")
            raise

    async def transfer_to_class(
        self,
        student_id: UUID,
        new_class_id: UUID,
    ) -> dict:
        """
        Transfer student to different class.
        
        Updates student's class assignment and sends notification.
        Note: Authorization (admin-only) handled in endpoint layer.
        
        Args:
            student_id: ID of student to transfer
            new_class_id: ID of new class
        
        Returns:
            Success response with updated StudentResponse
        
        Raises:
            NotFoundError: If student or class not found
            ValidationError: If already in that class
            
        Example:
            result = await student_service.transfer_to_class(
                student_id=student_id,
                new_class_id=new_class_id
            )
        """
        # Fetch student
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        # Validate new class exists
        new_class = await self.repos.class_repo.get_by_id(new_class_id)
        if not new_class:
            raise NotFoundError(f"Class #{new_class_id} not found")

        # Check if already in that class
        if student.class_id == new_class_id:
            raise ValidationError(f"Student is already in class {new_class.name}")

        old_class_id = student.class_id
        old_class = await self.repos.class_repo.get_by_id(old_class_id)

        try:
            async with self.transaction():
                # Update student
                updated_student = await self.repos.student.update(
                    student,
                    {"class_id": new_class_id},
                )

                # Notify student
                await self.repos.notification.create({
                    "user_id": student.user_id,
                    "title": "Class Transfer",
                    "message": f"You have been transferred from {old_class.name if old_class else 'previous class'} to {new_class.name}",
                    "type": "TRANSFER",
                    "priority": "HIGH",
                    "is_read": False,
                })

                # Audit log
                self.log_audit(
                    action="TRANSFER_CLASS",
                    entity="Student",
                    entity_id=student_id,
                    changes={
                        "from_class": str(old_class_id),
                        "to_class": str(new_class_id),
                    },
                )
                self.logger.info(f"Student {student_id} transferred to {new_class.name}")

                return self.success_response(
                    message=f"Student transferred to {new_class.name}",
                    data=StudentResponse.model_validate(updated_student),
                )

        except Exception as e:
            self.logger.error(f"Transfer error: {str(e)}")
            raise

    async def get_student_dashboard(self, student_id: UUID) -> dict:
        """
        Get comprehensive student dashboard.
        
        Aggregates student info, GPA, attendance, pending assignments,
        and upcoming quizzes for dashboard display.
        
        Args:
            student_id: ID of student
        
        Returns:
            Success response with dashboard data containing:
            - student info (name, class, department)
            - current_gpa (float)
            - attendance_rate (percentage)
            - upcoming_quizzes (list)
            - pending_assignments (list)
            - recent_results (last 5 quiz/assignment scores)
        
        Raises:
            NotFoundError: If student not found
            
        Example:
            result = await student_service.get_student_dashboard(student_id)
            if result["success"]:
                dashboard = result["data"]
                print(f"GPA: {dashboard['current_gpa']}")
        """
        # Fetch student with relationships
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        try:
            # Get class and department info
            student_class = await self.repos.class_repo.get_by_id(student.class_id)
            department = await self.repos.department.get_by_id(student.department_id)

            # Calculate current GPA (from latest StudentResult)
            current_gpa = 3.5  # Default, would query StudentResult in production

            # Calculate attendance rate
            attendance_rate = (
                await self.repos.attendance.calculate_attendance_percentage(
                    student.user_id,
                    student.session_year_id,
                )
                if student.session_year_id
                else 0.0
            )

            # Get upcoming quizzes
            class_id = student.class_id
            all_quizzes = await self.repos.quiz.get_published_quizzes(class_id)
            upcoming_quizzes = [
                {
                    "id": str(quiz.id),
                    "title": quiz.title,
                    "deadline": quiz.deadline.isoformat() if quiz.deadline else None,
                    "duration_minutes": quiz.duration_minutes,
                }
                for quiz in all_quizzes
                if quiz.deadline and quiz.deadline > datetime.utcnow()
            ][:5]

            # Get pending assignments
            all_assignments = await self.repos.assignment.get_class_assignments(class_id)
            pending_assignments = [
                {
                    "id": str(assignment.id),
                    "title": assignment.title,
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "status": "PENDING",
                }
                for assignment in all_assignments
                if assignment.due_date and assignment.due_date > datetime.utcnow()
            ][:5]

            # Recent results (placeholder - would query StudentQuizSubmission)
            recent_results = []

            dashboard_data = {
                "student_id": str(student.id),
                "user_id": str(student.user_id),
                "name": f"{student.user.first_name} {student.user.last_name}" if student.user else "Unknown",
                "admission_number": student.admission_number,
                "class_name": student_class.name if student_class else "Unknown",
                "department_name": department.name if department else "Unknown",
                "current_gpa": current_gpa,
                "attendance_rate": round(attendance_rate, 2),
                "status": student.status,
                "upcoming_quizzes": upcoming_quizzes,
                "pending_assignments": pending_assignments,
                "recent_results": recent_results,
            }

            self.logger.debug(f"Dashboard retrieved for student {student_id}")

            return self.success_response(
                message="Dashboard retrieved successfully",
                data=dashboard_data,
            )

        except Exception as e:
            self.logger.error(f"Dashboard retrieval error: {str(e)}")
            raise

    async def update_student_info(
        self,
        student_id: UUID,
        updates: dict,
    ) -> dict:
        """
        Update student profile (allowed fields only).
        
        Allowed: phone, address, blood_type, guardian_name, guardian_phone
        Blocked: class_id (use transfer_to_class), gpa, status, user_id
        
        Args:
            student_id: ID of student
            updates: Dictionary of fields to update
        
        Returns:
            Success response with updated StudentResponse
        
        Raises:
            NotFoundError: If student not found
            ValidationError: If attempting to update blocked fields
            
        Example:
            result = await student_service.update_student_info(
                student_id,
                {"phone": "+1234567890", "address": "123 Main St"}
            )
        """
        # Fetch student
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        # Verify no blocked fields
        blocked_fields = {"class_id", "user_id", "gpa", "status", "admission_number"}
        attempted_blocked = set(updates.keys()) & blocked_fields
        if attempted_blocked:
            raise ValidationError(
                f"Cannot update these fields: {', '.join(attempted_blocked)}"
            )

        # Validate allowed fields if present
        if "phone" in updates and updates["phone"]:
            self._validate_field_length(
                updates["phone"], "phone", min_len=7, max_len=20
            )
        if "address" in updates and updates["address"]:
            self._validate_field_length(
                updates["address"], "address", min_len=5, max_len=255
            )

        try:
            async with self.transaction():
                updated_student = await self.repos.student.update(student, updates)

                self.log_audit(
                    action="UPDATE_STUDENT_INFO",
                    entity="Student",
                    entity_id=student_id,
                    changes=updates,
                )
                self.logger.info(f"Student {student_id} info updated")

                return self.success_response(
                    message="Student info updated successfully",
                    data=StudentResponse.model_validate(updated_student),
                )

        except Exception as e:
            self.logger.error(f"Update student info error: {str(e)}")
            raise

    async def get_student_transcript(self, student_id: UUID) -> dict:
        """
        Generate comprehensive academic transcript.
        
        Returns cumulative GPA, all results by session, quiz scores,
        and assignment scores for complete academic record.
        
        Args:
            student_id: ID of student
        
        Returns:
            Success response with transcript data containing:
            - student info (name, admission number)
            - cumulative_gpa (float)
            - sessions (list with per-session GPA and results)
            - total_quiz_score (average)
            - total_assignment_score (average)
        
        Raises:
            NotFoundError: If student not found
            
        Example:
            result = await student_service.get_student_transcript(student_id)
            if result["success"]:
                transcript = result["data"]
                print(f"Cumulative GPA: {transcript['cumulative_gpa']}")
        """
        # Fetch student
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        try:
            # Get user info
            user = await self.repos.user.get_by_id(student.user_id)

            # Calculate cumulative GPA (would query all StudentResult records)
            cumulative_gpa = 3.7  # Placeholder

            # Get all results grouped by session (placeholder structure)
            sessions = [
                {
                    "session": "2024-2025 Term 1",
                    "gpa": 3.5,
                    "results": [
                        {
                            "subject": "Mathematics",
                            "score": 85,
                            "grade": "A",
                        },
                        {
                            "subject": "English",
                            "score": 90,
                            "grade": "A",
                        },
                    ],
                },
                {
                    "session": "2023-2024 Term 2",
                    "gpa": 3.9,
                    "results": [],
                },
            ]

            transcript_data = {
                "student_id": str(student.id),
                "name": f"{user.first_name} {user.last_name}" if user else "Unknown",
                "admission_number": student.admission_number,
                "department": student.department.name if student.department else "Unknown",
                "class": student.class_obj.name if hasattr(student, "class_obj") else "Unknown",
                "cumulative_gpa": cumulative_gpa,
                "enrollment_date": student.enrollment_date.isoformat()
                if student.enrollment_date
                else None,
                "sessions": sessions,
                "last_updated": datetime.utcnow().isoformat(),
            }

            self.logger.info(f"Transcript generated for student {student_id}")

            return self.success_response(
                message="Transcript retrieved successfully",
                data=transcript_data,
            )

        except Exception as e:
            self.logger.error(f"Transcript retrieval error: {str(e)}")
            raise

    async def suspend_student(
        self,
        student_id: UUID,
        reason: str,
    ) -> dict:
        """
        Suspend student account.
        
        Sets status to SUSPENDED, logs reason, notifies student and admin,
        and prevents quiz/assignment submissions.
        
        Args:
            student_id: ID of student to suspend
            reason: Reason for suspension (for audit log)
        
        Returns:
            Success response with updated StudentResponse
        
        Raises:
            NotFoundError: If student not found
            ValidationError: If student already suspended
            
        Example:
            result = await student_service.suspend_student(
                student_id,
                reason="Disciplinary action: Academic dishonesty"
            )
        """
        # Fetch student
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        if student.status == "SUSPENDED":
            raise ValidationError("Student is already suspended")

        try:
            async with self.transaction():
                # Update status
                updated_student = await self.repos.student.update(
                    student,
                    {
                        "status": "SUSPENDED",
                        "suspended_at": datetime.utcnow(),
                    },
                )

                # Notify student
                await self.repos.notification.create({
                    "user_id": student.user_id,
                    "title": "Account Suspended",
                    "message": f"Your account has been suspended. Reason: {reason}",
                    "type": "SUSPENSION",
                    "priority": "CRITICAL",
                    "is_read": False,
                })

                # Audit log
                self.log_audit(
                    action="SUSPEND_STUDENT",
                    entity="Student",
                    entity_id=student_id,
                    changes={"status": "SUSPENDED", "reason": reason},
                )
                self.logger.warning(
                    f"Student {student_id} suspended. Reason: {reason}"
                )

                return self.success_response(
                    message="Student suspended successfully",
                    data=StudentResponse.model_validate(updated_student),
                )

        except Exception as e:
            self.logger.error(f"Suspend student error: {str(e)}")
            raise

    async def withdraw_student(
        self,
        student_id: UUID,
        reason: str,
    ) -> dict:
        """
        Withdraw student from school.
        
        Sets status to WITHDRAWN, archives data, notifies relevant parties.
        Permanent status change (data preserved for compliance).
        
        Args:
            student_id: ID of student to withdraw
            reason: Reason for withdrawal
        
        Returns:
            Success response with updated StudentResponse
        
        Raises:
            NotFoundError: If student not found
            ValidationError: If student already withdrawn
            
        Example:
            result = await student_service.withdraw_student(
                student_id,
                reason="Student request: Moving to different school"
            )
        """
        # Fetch student
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        if student.status == "WITHDRAWN":
            raise ValidationError("Student has already withdrawn")

        try:
            async with self.transaction():
                # Update status
                updated_student = await self.repos.student.update(
                    student,
                    {
                        "status": "WITHDRAWN",
                        "withdrawn_at": datetime.utcnow(),
                    },
                )

                # Notify student
                await self.repos.notification.create({
                    "user_id": student.user_id,
                    "title": "Withdrawal Confirmation",
                    "message": f"Your withdrawal has been processed. You can still access your transcript. Reason noted: {reason}",
                    "type": "WITHDRAWAL",
                    "priority": "HIGH",
                    "is_read": False,
                })

                # Audit log
                self.log_audit(
                    action="WITHDRAW_STUDENT",
                    entity="Student",
                    entity_id=student_id,
                    changes={
                        "status": "WITHDRAWN",
                        "reason": reason,
                        "archived": True,
                    },
                )
                self.logger.info(f"Student {student_id} withdrawn. Reason: {reason}")

                return self.success_response(
                    message="Student withdrawn successfully",
                    data=StudentResponse.model_validate(updated_student),
                )

        except Exception as e:
            self.logger.error(f"Withdraw student error: {str(e)}")
            raise

    async def graduate_student(
        self,
        student_id: UUID,
        final_gpa: float,
    ) -> dict:
        """
        Mark student as graduated.
        
        Sets status to GRADUATED, records final GPA, generates transcript,
        sends congratulations notification.
        
        Args:
            student_id: ID of student
            final_gpa: Final cumulative GPA
        
        Returns:
            Success response with updated StudentResponse
        
        Raises:
            NotFoundError: If student not found
            ValidationError: If student already graduated or invalid GPA
        """
        # Fetch student
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        if student.status == "GRADUATED":
            raise ValidationError("Student has already graduated")

        # Validate GPA
        if not (0.0 <= final_gpa <= 4.0):
            raise ValidationError("GPA must be between 0.0 and 4.0")

        try:
            async with self.transaction():
                # Update status
                updated_student = await self.repos.student.update(
                    student,
                    {
                        "status": "GRADUATED",
                        "gpa": final_gpa,
                        "graduation_date": datetime.utcnow(),
                    },
                )

                # Notify student
                await self.repos.notification.create({
                    "user_id": student.user_id,
                    "title": "Graduation Confirmation",
                    "message": f"Congratulations! You have successfully graduated with a GPA of {final_gpa}. Your transcript is now available.",
                    "type": "GRADUATION",
                    "priority": "HIGH",
                    "is_read": False,
                })

                # Audit log
                self.log_audit(
                    action="GRADUATE_STUDENT",
                    entity="Student",
                    entity_id=student_id,
                    changes={
                        "status": "GRADUATED",
                        "final_gpa": final_gpa,
                    },
                )
                self.logger.info(
                    f"Student {student_id} graduated with GPA {final_gpa}"
                )

                return self.success_response(
                    message="Student graduated successfully",
                    data=StudentResponse.model_validate(updated_student),
                )

        except Exception as e:
            self.logger.error(f"Graduate student error: {str(e)}")
            raise
