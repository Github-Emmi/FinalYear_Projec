"""
Assignment Service - Assignment creation, submission, and grading management.

Provides:
- Assignment creation with due dates
- Student submission handling with late detection
- Staff grading with feedback
- Submission tracking and analytics
- File storage integration (local/S3)
"""

from datetime import datetime, date as date_type
from typing import Optional
from uuid import UUID

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    ForbiddenError,
)
from app.models.assignment import Assignment
from app.repositories.factory import RepositoryFactory
from app.schemas.assignment import (
    AssignmentResponse,
    SubmissionResponse,
    SubmissionSummary,
)
from app.services.base import BaseService


class AssignmentService(BaseService[Assignment]):
    """
    Assignment service for managing student coursework.
    
    Handles:
    - Assignment creation with deadlines and scoring
    - Student submissions with late detection
    - Staff grading with constructive feedback
    - Submission tracking and pagination
    - Assignment lifecycle (active → closed)
    - Comprehensive audit logging
    
    Usage:
        assignment_service = AssignmentService(repos)
        
        # Create assignment
        assignment = await assignment_service.create_assignment(
            staff_id=staff_id,
            class_id=class_id,
            title="Essay Assignment",
            instructions="Write a 5-page essay...",
            due_date=due_date,
            max_score=100
        )
        
        # Submit assignment
        submission = await assignment_service.submit_assignment(
            assignment_id=assignment.id,
            student_id=student_id,
            file_path="submissions/essay.pdf"
        )
        
        # Grade submission
        result = await assignment_service.grade_assignment(
            submission_id=submission_id,
            staff_id=staff_id,
            score=85,
            feedback="Excellent work! Well-structured argument."
        )
    """

    async def create_assignment(
        self,
        staff_id: UUID,
        class_id: UUID,
        title: str,
        instructions: str,
        due_date: datetime,
        max_score: int,
    ) -> dict:
        """
        Create a new assignment for a class.
        
        Validates staff and class existence, deadline in future, and max_score > 0.
        Creates Assignment record with ACTIVE status and notifies all students in class.
        
        Args:
            staff_id: ID of staff member creating assignment
            class_id: ID of class for assignment
            title: Assignment title (e.g., "Chapter 5 Essay")
            instructions: Detailed assignment instructions
            due_date: When assignment is due (must be future datetime)
            max_score: Maximum points possible (must be > 0)
        
        Returns:
            Success response with AssignmentResponse data (status=ACTIVE)
        
        Raises:
            NotFoundError: If staff or class not found
            ValidationError: If due_date not future, max_score <= 0, or invalid fields
        
        Example:
            result = await assignment_service.create_assignment(
                staff_id=staff_id,
                class_id=class_id,
                title="Algebra Problem Set",
                instructions="Complete problems 1-20 from Chapter 7",
                due_date=datetime.utcnow() + timedelta(days=7),
                max_score=50
            )
        """
        # Validate staff exists
        staff = await self.repos.user.get_by_id(staff_id)
        if not staff:
            raise NotFoundError(f"Staff member #{staff_id} not found")

        # Validate class exists
        class_obj = await self.repos.class_repo.get_by_id(class_id)
        if not class_obj:
            raise NotFoundError(f"Class #{class_id} not found")

        # Validate due_date in future
        if due_date <= datetime.utcnow():
            raise ValidationError("Due date must be in the future")

        # Validate max_score > 0
        if max_score <= 0:
            raise ValidationError("Max score must be greater than 0")

        # Validate fields
        self._validate_field_length(title, "title", min_len=3, max_len=200)
        self._validate_field_length(
            instructions, "instructions", min_len=10, max_len=5000
        )

        try:
            async with self.transaction():
                # Create assignment
                assignment = await self.repos.assignment.create({
                    "staff_id": staff_id,
                    "class_id": class_id,
                    "title": title,
                    "instructions": instructions,
                    "due_date": due_date,
                    "max_score": max_score,
                    "status": "ACTIVE",
                    "created_at": datetime.utcnow(),
                })

                # Get students in class
                students = await self.repos.student.get_by_class(class_id)

                # Notify all students
                for student in students:
                    if student.status == "ACTIVE":
                        await self.repos.notification.create({
                            "user_id": student.user_id,
                            "title": f"New Assignment: {title}",
                            "message": (
                                f"A new assignment '{title}' has been posted. "
                                f"Due: {due_date.strftime('%Y-%m-%d %H:%M')}. "
                                f"Max Score: {max_score}"
                            ),
                            "type": "ASSIGNMENT_CREATED",
                            "priority": "HIGH",
                            "is_read": False,
                        })

                # Audit log
                self.log_audit(
                    action="CREATE_ASSIGNMENT",
                    entity="Assignment",
                    entity_id=assignment.id,
                    user_id=staff_id,
                    changes={
                        "title": title,
                        "due_date": due_date.isoformat(),
                        "max_score": max_score,
                        "students_notified": len([s for s in students if s.status == "ACTIVE"]),
                    },
                )
                self.logger.info(
                    f"Assignment '{title}' created for class {class_id} "
                    f"by staff {staff_id}"
                )

                return self.success_response(
                    message="Assignment created successfully",
                    data=AssignmentResponse.model_validate(assignment),
                )

        except Exception as e:
            self.logger.error(f"Create assignment error: {str(e)}")
            raise

    async def submit_assignment(
        self,
        assignment_id: UUID,
        student_id: UUID,
        file_path: str,
    ) -> dict:
        """
        Submit an assignment.
        
        Validates assignment exists, is not closed, and student is enrolled.
        Detects late submissions. Prevents duplicate submissions by checking
        for existing submission and updating instead.
        
        Args:
            assignment_id: ID of assignment
            student_id: ID of student submitting
            file_path: Path to submitted file (S3 or local)
        
        Returns:
            Success response with SubmissionResponse containing:
            - submission_id: ID of submission
            - status: "SUBMITTED"
            - is_late: Boolean if submitted after due_date
            - submitted_at: Timestamp
        
        Raises:
            NotFoundError: If assignment or student not found
            ForbiddenError: If student not in assignment's class
            ValidationError: If assignment closed or file_path invalid
        
        Example:
            result = await assignment_service.submit_assignment(
                assignment_id=assignment_id,
                student_id=student_id,
                file_path="s3://bucket/submissions/2024-03-04-essay.pdf"
            )
            if result["data"]["is_late"]:
                print("Submitted late!")
        """
        # Validate assignment exists
        assignment = await self.repos.assignment.get_by_id(assignment_id)
        if not assignment:
            raise NotFoundError(f"Assignment #{assignment_id} not found")

        # Validate assignment not closed
        if assignment.status == "CLOSED":
            raise ValidationError("Assignment is closed and no longer accepts submissions")

        # Validate student exists
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        # Validate student in assignment's class
        if student.class_id != assignment.class_id:
            raise ForbiddenError(
                f"Student is not enrolled in class {assignment.class_id}"
            )

        # Validate file_path
        self._validate_field_length(file_path, "file_path", min_len=5, max_len=500)

        # Check for duplicate submission (idempotent)
        existing_submission = (
            await self.repos.assignment_submission.get_by_assignment_and_student(
                assignment_id, student_id
            )
        )

        try:
            async with self.transaction():
                now = datetime.utcnow()
                is_late = now > assignment.due_date

                if existing_submission:
                    # Update existing submission instead of creating duplicate
                    submission = await self.repos.assignment_submission.update(
                        existing_submission,
                        {
                            "file_path": file_path,
                            "submitted_at": now,
                            "is_late": is_late,
                            "status": "SUBMITTED",
                        },
                    )
                    message = "Assignment resubmitted successfully"
                else:
                    # Create new submission
                    submission = await self.repos.assignment_submission.create({
                        "assignment_id": assignment_id,
                        "student_id": student_id,
                        "file_path": file_path,
                        "submitted_at": now,
                        "is_late": is_late,
                        "status": "SUBMITTED",
                    })
                    message = "Assignment submitted successfully"

                # Audit log
                self.log_audit(
                    action="SUBMIT_ASSIGNMENT",
                    entity="AssignmentSubmission",
                    entity_id=submission.id,
                    user_id=student_id,
                    changes={
                        "assignment_id": str(assignment_id),
                        "is_late": is_late,
                        "file_path": file_path,
                    },
                )
                self.logger.info(
                    f"Student {student_id} submitted assignment {assignment_id} "
                    f"{'(late)' if is_late else '(on time)'}"
                )

                return self.success_response(
                    message=message,
                    data={
                        "submission_id": str(submission.id),
                        "assignment_id": str(assignment_id),
                        "student_id": str(student_id),
                        "status": "SUBMITTED",
                        "is_late": is_late,
                        "submitted_at": now.isoformat(),
                    },
                )

        except Exception as e:
            self.logger.error(f"Submit assignment error: {str(e)}")
            raise

    async def grade_assignment(
        self,
        submission_id: UUID,
        staff_id: UUID,
        score: int,
        feedback: str,
    ) -> dict:
        """
        Grade a student's assignment submission.
        
        Validates submission exists, score is valid (0-max_score), and staff
        is assignment creator. Updates submission with grade and feedback,
        sends notification to student.
        
        Args:
            submission_id: ID of submission to grade
            staff_id: ID of staff member grading (must be assignment creator)
            score: Points earned (0 to assignment.max_score)
            feedback: Constructive feedback for student
        
        Returns:
            Success response with updated SubmissionResponse (status=GRADED)
        
        Raises:
            NotFoundError: If submission not found
            ForbiddenError: If staff didn't create the assignment
            ValidationError: If score invalid or feedback empty
        
        Example:
            result = await assignment_service.grade_assignment(
                submission_id=submission_id,
                staff_id=staff_id,
                score=92,
                feedback="Excellent analysis! Minor grammatical issues on page 3."
            )
        """
        # Validate submission exists
        submission = await self.repos.assignment_submission.get_by_id(submission_id)
        if not submission:
            raise NotFoundError(f"Submission #{submission_id} not found")

        # Fetch assignment
        assignment = await self.repos.assignment.get_by_id(submission.assignment_id)
        if not assignment:
            raise NotFoundError(f"Assignment #{submission.assignment_id} not found")

        # Validate staff ownership
        if assignment.staff_id != staff_id:
            raise ForbiddenError(
                "You can only grade submissions for your own assignments"
            )

        # Validate score
        if not (0 <= score <= assignment.max_score):
            raise ValidationError(
                f"Score must be between 0 and {assignment.max_score}"
            )

        # Validate feedback
        self._validate_field_length(
            feedback, "feedback", min_len=1, max_len=2000
        )

        try:
            async with self.transaction():
                # Update submission
                graded_submission = await self.repos.assignment_submission.update(
                    submission,
                    {
                        "score": score,
                        "feedback": feedback,
                        "graded_at": datetime.utcnow(),
                        "status": "GRADED",
                    },
                )

                # Notify student
                student = await self.repos.student.get_by_id(submission.student_id)
                if student:
                    await self.repos.notification.create({
                        "user_id": student.user_id,
                        "title": f"Assignment Graded: {assignment.title}",
                        "message": (
                            f"Your assignment '{assignment.title}' has been graded. "
                            f"Score: {score}/{assignment.max_score}"
                        ),
                        "type": "ASSIGNMENT_GRADED",
                        "priority": "HIGH",
                        "is_read": False,
                    })

                # Audit log
                self.log_audit(
                    action="GRADE_ASSIGNMENT",
                    entity="AssignmentSubmission",
                    entity_id=submission_id,
                    user_id=staff_id,
                    changes={
                        "score": score,
                        "max_score": assignment.max_score,
                        "percentage": round(score / assignment.max_score * 100, 2),
                    },
                )
                self.logger.info(
                    f"Submission {submission_id} graded: {score}/{assignment.max_score}"
                )

                return self.success_response(
                    message="Assignment graded successfully",
                    data={
                        "submission_id": str(submission_id),
                        "assignment_id": str(assignment.id),
                        "student_id": str(submission.student_id),
                        "score": score,
                        "max_score": assignment.max_score,
                        "percentage": round(score / assignment.max_score * 100, 2),
                        "status": "GRADED",
                        "graded_at": datetime.utcnow().isoformat(),
                    },
                )

        except Exception as e:
            self.logger.error(f"Grade assignment error: {str(e)}")
            raise

    async def get_assignment_submissions(
        self,
        assignment_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """
        Get all submissions for an assignment (paginated).
        
        Returns list of submission summaries including student name, score,
        submission status, and whether submitted late.
        
        Args:
            assignment_id: ID of assignment
            skip: Pagination skip (default 0)
            limit: Pagination limit (default 20, max 100)
        
        Returns:
            Success response with data containing:
            - submissions: List of SubmissionSummary objects
            - total: Total submission count
            - skip, limit: Pagination parameters
        
        Raises:
            NotFoundError: If assignment not found
        
        Example:
            result = await assignment_service.get_assignment_submissions(
                assignment_id=assignment_id,
                skip=0,
                limit=50
            )
            for sub in result["data"]["submissions"]:
                print(f"{sub['student_name']}: {sub['score']} points")
        """
        # Validate assignment exists
        assignment = await self.repos.assignment.get_by_id(assignment_id)
        if not assignment:
            raise NotFoundError(f"Assignment #{assignment_id} not found")

        # Validate pagination
        limit = min(limit, 100)
        if skip < 0:
            skip = 0

        try:
            # Fetch submissions with pagination
            submissions, total = (
                await self.repos.assignment_submission.get_by_assignment_paginated(
                    assignment_id, skip=skip, limit=limit
                )
            )

            # Build submission summaries
            submission_summaries = []
            for sub in submissions:
                student = await self.repos.student.get_by_id(sub.student_id)
                student_name = (
                    f"{student.user.first_name} {student.user.last_name}"
                    if student and student.user
                    else "Unknown"
                )

                submission_summaries.append({
                    "submission_id": str(sub.id),
                    "student_id": str(sub.student_id),
                    "student_name": student_name,
                    "score": sub.score,
                    "max_score": assignment.max_score,
                    "percentage": (
                        round(sub.score / assignment.max_score * 100, 1)
                        if sub.score is not None
                        else None
                    ),
                    "submitted_at": (
                        sub.submitted_at.isoformat() if sub.submitted_at else None
                    ),
                    "is_late": sub.is_late,
                    "grading_status": sub.status,
                    "graded_at": (
                        sub.graded_at.isoformat() if sub.graded_at else None
                    ),
                })

            self.logger.info(
                f"Retrieved {len(submissions)} submissions for assignment {assignment_id}"
            )

            return self.success_response(
                message="Assignment submissions retrieved successfully",
                data={
                    "assignment_id": str(assignment_id),
                    "submissions": submission_summaries,
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                },
            )

        except Exception as e:
            self.logger.error(f"Get assignment submissions error: {str(e)}")
            raise

    async def close_assignment(
        self,
        assignment_id: UUID,
        staff_id: UUID,
    ) -> dict:
        """
        Close an assignment (prevent further submissions).
        
        Updates assignment status to CLOSED. After closing, no new submissions
        are accepted, though existing submissions can still be graded.
        
        Args:
            assignment_id: ID of assignment to close
            staff_id: ID of staff member (must be assignment creator)
        
        Returns:
            Success response with updated AssignmentResponse (status=CLOSED)
        
        Raises:
            NotFoundError: If assignment not found
            ForbiddenError: If staff didn't create the assignment
            ValidationError: If assignment already closed
        
        Example:
            result = await assignment_service.close_assignment(
                assignment_id=assignment_id,
                staff_id=staff_id
            )
        """
        # Validate assignment exists
        assignment = await self.repos.assignment.get_by_id(assignment_id)
        if not assignment:
            raise NotFoundError(f"Assignment #{assignment_id} not found")

        # Validate staff ownership
        if assignment.staff_id != staff_id:
            raise ForbiddenError(
                "You can only close your own assignments"
            )

        # Check if already closed
        if assignment.status == "CLOSED":
            raise ValidationError("Assignment is already closed")

        try:
            async with self.transaction():
                # Update assignment status
                closed_assignment = await self.repos.assignment.update(
                    assignment,
                    {"status": "CLOSED", "closed_at": datetime.utcnow()},
                )

                # Audit log
                self.log_audit(
                    action="CLOSE_ASSIGNMENT",
                    entity="Assignment",
                    entity_id=assignment_id,
                    user_id=staff_id,
                    changes={"status": "CLOSED"},
                )
                self.logger.info(f"Assignment {assignment_id} closed")

                return self.success_response(
                    message="Assignment closed successfully",
                    data=AssignmentResponse.model_validate(closed_assignment),
                )

        except Exception as e:
            self.logger.error(f"Close assignment error: {str(e)}")
            raise
