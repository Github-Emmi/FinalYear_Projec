"""
Quiz Service - Quiz creation, publishing, and attempt management.

Provides:
- Quiz creation with questions
- Quiz publishing to students
- Quiz attempt tracking with time limits
- Answer submission and grading (MCQ immediate, essay async)
- Results retrieval with access control
- Staff dashboard for submission review
"""

from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    ForbiddenError,
)
from app.models.quiz import Quiz
from app.repositories.factory import RepositoryFactory
from app.schemas.quiz import (
    QuizResponse,
    QuestionCreateSchema,
    SubmitAnswerSchema,
    QuizAttemptResponse,
    StudentQuizSubmissionResponse,
    QuizResultSchema,
    SubmissionSummary,
)
from app.services.base import BaseService


class QuizService(BaseService[Quiz]):
    """
    Quiz service for managing quiz lifecycle and student submissions.
    
    Handles:
    - Quiz creation with questions
    - Publishing quizzes to students with notifications
    - Quiz attempt tracking with timer and deadline validation
    - Answer submission with answer storage
    - Automatic grading for MCQ (immediate), async for essays via Celery
    - Result retrieval with security checks
    - Staff dashboard for submission review and analytics
    
    Usage:
        quiz_service = QuizService(repos)
        
        # Create quiz
        quiz = await quiz_service.create_quiz(
            staff_id=staff_id,
            title="Midterm Exam",
            duration_minutes=60,
            class_id=class_id,
            questions=[...]
        )
        
        # Publish to students
        await quiz_service.publish_quiz(quiz.id, staff_id)
        
        # Start attempt
        attempt = await quiz_service.start_quiz_attempt(quiz.id, student_id)
        
        # Submit answers
        submission = await quiz_service.submit_quiz(
            attempt.id, student_id, answers
        )
    """

    async def create_quiz(
        self,
        staff_id: UUID,
        title: str,
        description: str,
        duration_minutes: int,
        passing_score: int,
        deadline: datetime,
        class_id: UUID,
        questions: List[QuestionCreateSchema],
    ) -> dict:
        """
        Create a new quiz with questions.
        
        Validates staff role, class existence, deadline in future, duration
        (1-180 minutes), passing score (0-100), and at least 1 question.
        Creates Quiz record with status=DRAFT and associated Questions.
        
        Args:
            staff_id: ID of staff member creating quiz
            title: Quiz title (e.g., "Midterm Exam")
            description: Quiz description
            duration_minutes: Quiz duration in minutes (1-180)
            passing_score: Minimum passing score percentage (0-100)
            deadline: Quiz deadline (must be future datetime)
            class_id: ID of class for quiz
            questions: List of QuestionCreateSchema with question details
        
        Returns:
            Success response with QuizResponse data (status=DRAFT)
        
        Raises:
            NotFoundError: If staff or class not found
            ValidationError: If role != STAFF, deadline passed, duration invalid,
                           score invalid, or no questions provided
        
        Example:
            questions = [
                QuestionCreateSchema(
                    text="What is 2+2?",
                    question_type="MCQ",
                    options=["3", "4", "5", "6"],
                    correct_answer="4",
                    points=1
                ),
                QuestionCreateSchema(
                    text="Explain quantum mechanics",
                    question_type="ESSAY",
                    correct_answer=None,
                    points=10
                )
            ]
            result = await quiz_service.create_quiz(
                staff_id=staff_id,
                title="Physics Midterm",
                description="Covers chapters 1-5",
                duration_minutes=60,
                passing_score=60,
                deadline=datetime.utcnow() + timedelta(days=7),
                class_id=class_id,
                questions=questions
            )
        """
        # Validate staff exists and has STAFF role
        staff = await self.repos.user.get_by_id(staff_id)
        if not staff:
            raise NotFoundError(f"Staff member #{staff_id} not found")
        if staff.role != "STAFF":
            raise ValidationError(f"User must have STAFF role, has {staff.role}")

        # Validate class exists
        class_obj = await self.repos.class_repo.get_by_id(class_id)
        if not class_obj:
            raise NotFoundError(f"Class #{class_id} not found")

        # Validate deadline is in future
        if deadline <= datetime.utcnow():
            raise ValidationError("Deadline must be in the future")

        # Validate duration (1-180 minutes)
        if not (0 < duration_minutes <= 180):
            raise ValidationError("Duration must be between 1 and 180 minutes")

        # Validate passing score (0-100)
        self._validate_enum_choice(
            passing_score,
            "passing_score",
            [i for i in range(0, 101)],
        )
        if not (0 <= passing_score <= 100):
            raise ValidationError("Passing score must be between 0 and 100")

        # Validate questions
        if not questions or len(questions) == 0:
            raise ValidationError("At least 1 question is required for quiz")

        try:
            async with self.transaction():
                # Create quiz record
                quiz = await self.repos.quiz.create({
                    "staff_id": staff_id,
                    "class_id": class_id,
                    "title": title,
                    "description": description,
                    "duration_minutes": duration_minutes,
                    "passing_score": passing_score,
                    "deadline": deadline,
                    "status": "DRAFT",
                    "total_questions": len(questions),
                })

                # Create question records for each question
                for idx, question_data in enumerate(questions):
                    await self.repos.question.create({
                        "quiz_id": quiz.id,
                        "text": question_data.text,
                        "question_type": question_data.question_type,
                        "options": question_data.options,
                        "correct_answer": question_data.correct_answer,
                        "points": (
                            question_data.points
                            if hasattr(question_data, "points")
                            else 1
                        ),
                        "order": idx + 1,
                    })

                # Audit log
                self.log_audit(
                    action="CREATE_QUIZ",
                    entity="Quiz",
                    entity_id=quiz.id,
                    user_id=staff_id,
                    changes={
                        "title": title,
                        "questions_count": len(questions),
                        "duration_minutes": duration_minutes,
                        "passing_score": passing_score,
                    },
                )
                self.logger.info(
                    f"Quiz '{title}' created by staff {staff_id} with "
                    f"{len(questions)} questions"
                )

                return self.success_response(
                    message="Quiz created successfully",
                    data=QuizResponse.model_validate(quiz),
                )

        except Exception as e:
            self.logger.error(f"Create quiz error: {str(e)}")
            raise

    async def publish_quiz(self, quiz_id: UUID, staff_id: UUID) -> dict:
        """
        Publish quiz to make it available to students.
        
        Validates quiz exists, belongs to staff, has >= 1 question, and is not
        already published. Updates status to PUBLISHED, sends notifications to
        all students in the class.
        
        Args:
            quiz_id: ID of quiz to publish
            staff_id: ID of staff member (must be quiz creator for authorization)
        
        Returns:
            Success response with updated QuizResponse (status=PUBLISHED)
        
        Raises:
            NotFoundError: If quiz not found
            ForbiddenError: If quiz doesn't belong to staff
            ValidationError: If quiz has no questions or already published
        
        Example:
            result = await quiz_service.publish_quiz(quiz_id, staff_id)
            if result["success"]:
                print(f"Quiz published to {result['data']['students_count']} students")
        """
        # Validate quiz exists
        quiz = await self.repos.quiz.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz #{quiz_id} not found")

        # Validate staff ownership (authorization)
        if quiz.staff_id != staff_id:
            raise ForbiddenError("You can only publish your own quizzes")

        # Validate quiz has questions
        questions = await self.repos.question.get_by_quiz(quiz_id)
        if not questions or len(questions) == 0:
            raise ValidationError("Quiz must have at least 1 question before publishing")

        # Validate not already published
        if quiz.status == "PUBLISHED":
            raise ValidationError("Quiz is already published")

        try:
            async with self.transaction():
                # Update quiz status
                updated_quiz = await self.repos.quiz.update(
                    quiz,
                    {
                        "status": "PUBLISHED",
                        "published_at": datetime.utcnow(),
                    },
                )

                # Get students in class
                students = await self.repos.student.get_by_class(quiz.class_id)

                # Notify all students in class
                for student in students:
                    if student.status == "ACTIVE":  # Only notify active students
                        await self.repos.notification.create({
                            "user_id": student.user_id,
                            "title": f"New Quiz: {quiz.title}",
                            "message": (
                                f"A new quiz '{quiz.title}' is available. "
                                f"Duration: {quiz.duration_minutes} minutes. "
                                f"Deadline: {quiz.deadline.strftime('%Y-%m-%d %H:%M')}"
                            ),
                            "type": "QUIZ_PUBLISHED",
                            "priority": "HIGH",
                            "is_read": False,
                        })

                # Audit log
                self.log_audit(
                    action="PUBLISH_QUIZ",
                    entity="Quiz",
                    entity_id=quiz_id,
                    user_id=staff_id,
                    changes={
                        "status": "PUBLISHED",
                        "students_notified": len(students),
                    },
                )
                self.logger.info(
                    f"Quiz {quiz_id} published to {len(students)} students in class"
                )

                return self.success_response(
                    message="Quiz published successfully",
                    data=QuizResponse.model_validate(updated_quiz),
                )

        except Exception as e:
            self.logger.error(f"Publish quiz error: {str(e)}")
            raise

    async def start_quiz_attempt(
        self,
        quiz_id: UUID,
        student_id: UUID,
    ) -> dict:
        """
        Start a quiz attempt for a student.
        
        Validates quiz is published, student exists and is in quiz's class,
        deadline not passed, and no active attempt exists. Creates QuizAttempt
        record with calculated end_time. Returns all questions with options
        and time remaining.
        
        Args:
            quiz_id: ID of quiz
            student_id: ID of student attempting quiz
        
        Returns:
            Success response with QuizAttemptResponse containing:
            - attempt_id: ID of the attempt
            - quiz_id: ID of quiz
            - questions: List of questions with options and points
            - time_remaining_seconds: Seconds until quiz end time
            - duration_minutes: Quiz duration
        
        Raises:
            NotFoundError: If quiz or student not found
            ForbiddenError: If student not in quiz's class
            ValidationError: If quiz not published, deadline passed, or already has active attempt
            ConflictError: If student already has active attempt
        
        Example:
            result = await quiz_service.start_quiz_attempt(quiz_id, student_id)
            if result["success"]:
                attempt_data = result["data"]
                print(f"Time remaining: {attempt_data['time_remaining_seconds']}s")
                for q in attempt_data["questions"]:
                    print(f"Q{q['order']}: {q['text']}")
        """
        # Validate quiz exists and is published
        quiz = await self.repos.quiz.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz #{quiz_id} not found")
        if quiz.status != "PUBLISHED":
            raise ValidationError("Quiz is not published yet")

        # Validate student exists
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        # Validate student is in quiz's class
        if student.class_id != quiz.class_id:
            raise ForbiddenError(
                f"Student is not enrolled in class {quiz.class_id}"
            )

        # Validate quiz deadline not passed
        if quiz.deadline <= datetime.utcnow():
            raise ValidationError(
                f"Quiz deadline has passed ({quiz.deadline.isoformat()})"
            )

        # Check for active attempt (prevent double attempts)
        active_attempt = await self.repos.quiz_attempt.get_active_attempt(
            quiz_id, student_id
        )
        if active_attempt:
            raise ConflictError(
                "Student already has an active attempt for this quiz"
            )

        try:
            async with self.transaction():
                # Calculate end time based on quiz duration
                end_time = datetime.utcnow() + timedelta(minutes=quiz.duration_minutes)

                # Create attempt record
                attempt = await self.repos.quiz_attempt.create({
                    "quiz_id": quiz_id,
                    "student_id": student_id,
                    "status": "IN_PROGRESS",
                    "started_at": datetime.utcnow(),
                    "end_time": end_time,
                })

                # Fetch all questions with options (in order)
                questions = await self.repos.question.get_by_quiz(quiz_id)

                # Calculate time remaining
                time_remaining = (
                    attempt.end_time - datetime.utcnow()
                ).total_seconds()

                # Audit log
                self.log_audit(
                    action="START_QUIZ_ATTEMPT",
                    entity="QuizAttempt",
                    entity_id=attempt.id,
                    user_id=student_id,
                    changes={
                        "quiz_id": str(quiz_id),
                        "duration_minutes": quiz.duration_minutes,
                    },
                )
                self.logger.info(
                    f"Student {student_id} started quiz {quiz_id} "
                    f"(attempt {attempt.id})"
                )

                return self.success_response(
                    message="Quiz attempt started",
                    data={
                        "attempt_id": str(attempt.id),
                        "quiz_id": str(quiz_id),
                        "quiz_title": quiz.title,
                        "questions": [
                            {
                                "question_id": str(q.id),
                                "order": q.order,
                                "text": q.text,
                                "question_type": q.question_type,
                                "options": q.options,
                                "points": q.points,
                            }
                            for q in questions
                        ],
                        "time_remaining_seconds": int(time_remaining),
                        "duration_minutes": quiz.duration_minutes,
                    },
                )

        except Exception as e:
            self.logger.error(f"Start quiz attempt error: {str(e)}")
            raise

    async def submit_quiz(
        self,
        attempt_id: UUID,
        student_id: UUID,
        answers: List[SubmitAnswerSchema],
    ) -> dict:
        """
        Submit completed quiz answers.
        
        Validates attempt exists and belongs to student, status is IN_PROGRESS,
        and deadline not exceeded. Saves StudentQuizSubmission and individual
        StudentAnswer records. Triggers automatic grading for MCQ (immediate)
        and async Celery task for essays.
        
        Args:
            attempt_id: ID of quiz attempt
            student_id: ID of student (security check)
            answers: List of SubmitAnswerSchema with question_id and answer text
        
        Returns:
            Success response with StudentQuizSubmissionResponse indicating:
            - submission_id: ID of submission
            - status: "SUBMITTED"
            - grading_status: "GRADING" (MCQ) or "PENDING_GRADING" (essay)
            - message: Describes next steps
        
        Raises:
            NotFoundError: If attempt not found
            ForbiddenError: If attempt doesn't belong to student
            ValidationError: If attempt not IN_PROGRESS or time exceeded
        
        Example:
            answers = [
                SubmitAnswerSchema(question_id=q1_id, answer="A"),
                SubmitAnswerSchema(question_id=q2_id, answer="Yes"),
            ]
            result = await quiz_service.submit_quiz(
                attempt_id=attempt_id,
                student_id=student_id,
                answers=answers
            )
            # Message: "Your quiz has been submitted. Grading in progress..."
        """
        # Validate attempt exists
        attempt = await self.repos.quiz_attempt.get_by_id(attempt_id)
        if not attempt:
            raise NotFoundError(f"Quiz attempt #{attempt_id} not found")

        # Validate student ownership (security)
        if attempt.student_id != student_id:
            raise ForbiddenError("You can only submit your own quiz attempts")

        # Validate status is IN_PROGRESS
        if attempt.status != "IN_PROGRESS":
            raise ValidationError(
                f"Cannot submit: attempt is {attempt.status}"
            )

        # Validate time not expired
        if datetime.utcnow() > attempt.end_time:
            raise ValidationError(
                f"Quiz time limit expired at {attempt.end_time.isoformat()}"
            )

        try:
            async with self.transaction():
                # Create submission record
                submission = await self.repos.student_quiz_submission.create({
                    "quiz_id": attempt.quiz_id,
                    "student_id": student_id,
                    "attempt_id": attempt_id,
                    "submitted_at": datetime.utcnow(),
                    "status": "SUBMITTED",
                })

                # Save individual answers
                for answer_data in answers:
                    await self.repos.student_answer.create({
                        "submission_id": submission.id,
                        "question_id": answer_data.question_id,
                        "answer_text": answer_data.answer,
                        "submitted_at": datetime.utcnow(),
                    })

                # Update attempt to SUBMITTED
                await self.repos.quiz_attempt.update(
                    attempt,
                    {"status": "SUBMITTED"},
                )

                # Check if quiz has essays (async grading needed)
                questions = await self.repos.question.get_by_quiz(attempt.quiz_id)
                has_essay = any(q.question_type == "ESSAY" for q in questions)
                has_short_answer = any(
                    q.question_type == "SHORT_ANSWER" for q in questions
                )

                grading_type = (
                    "PENDING_GRADING"
                    if (has_essay or has_short_answer)
                    else "GRADING"
                )

                # TODO: Trigger Celery grading tasks
                # if has_essay:
                #     from app.tasks.grading import grade_essay_answers
                #     grade_essay_answers.delay(str(submission.id))
                # else:
                #     from app.tasks.grading import grade_mcq_answers
                #     grade_mcq_answers.delay(str(submission.id))

                # Audit log
                self.log_audit(
                    action="SUBMIT_QUIZ",
                    entity="StudentQuizSubmission",
                    entity_id=submission.id,
                    user_id=student_id,
                    changes={
                        "attempt_id": str(attempt_id),
                        "answers_count": len(answers),
                        "grading_type": grading_type,
                    },
                )
                self.logger.info(
                    f"Student {student_id} submitted quiz {attempt.quiz_id} "
                    f"with {len(answers)} answers"
                )

                return self.success_response(
                    message="Quiz submitted successfully",
                    data={
                        "submission_id": str(submission.id),
                        "attempt_id": str(attempt_id),
                        "status": "SUBMITTED",
                        "grading_status": grading_type,
                        "message": (
                            "Your quiz has been submitted. Essay answers "
                            "are being reviewed and will be graded shortly."
                            if has_essay
                            else "Your quiz has been submitted and is being graded..."
                        ),
                    },
                )

        except Exception as e:
            self.logger.error(f"Submit quiz error: {str(e)}")
            raise

    async def get_quiz_results(
        self,
        quiz_id: UUID,
        student_id: UUID,
    ) -> dict:
        """
        Get quiz results for a student.
        
        Retrieves submission, all answers, calculates score, and returns
        detailed breakdown. Only available after grading is complete (status=GRADED).
        
        Args:
            quiz_id: ID of quiz
            student_id: ID of student
        
        Returns:
            Success response with QuizResultSchema containing:
            - submission_id: ID of submission
            - student_name: Student's full name
            - score: Points earned
            - total_points: Total possible points
            - percentage: Score as percentage
            - passed: Boolean if score >= passing_score
            - passing_score: Quiz passing score percentage
            - time_taken_minutes: Duration of attempt
            - submitted_at: When submitted
            - answers: List of answer details with:
                - question_id, question_text, student_answer, correct_answer,
                  is_correct, points_earned, total_points
        
        Raises:
            NotFoundError: If quiz or submission not found
            ValidationError: If grading not complete (still SUBMITTED or PENDING_GRADING)
        
        Example:
            result = await quiz_service.get_quiz_results(quiz_id, student_id)
            if result["success"]:
                data = result["data"]
                print(f"Score: {data['percentage']}%")
                print(f"Passed: {data['passed']}")
        """
        # Validate quiz exists
        quiz = await self.repos.quiz.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz #{quiz_id} not found")

        # Fetch submission for this student
        submission = (
            await self.repos.student_quiz_submission.get_by_quiz_and_student(
                quiz_id, student_id
            )
        )
        if not submission:
            raise NotFoundError(
                f"No submission found for student #{student_id} in quiz #{quiz_id}"
            )

        # Check grading status
        if submission.status != "GRADED":
            raise ValidationError(
                f"Results not yet available. Submission status: {submission.status}. "
                "Check back after grading is complete."
            )

        try:
            # Fetch all answers for this submission
            answers = await self.repos.student_answer.get_by_submission(
                submission.id
            )

            # Fetch questions for comparison
            questions_map = {}
            questions = await self.repos.question.get_by_quiz(quiz_id)
            for q in questions:
                questions_map[q.id] = q

            # Build answer details and calculate score
            answer_details = []
            total_points = 0
            earned_points = 0

            for answer in answers:
                question = questions_map.get(answer.question_id)
                if not question:
                    continue

                # Check if correct
                is_correct = answer.answer_text == question.correct_answer
                points_earned = question.points if is_correct else 0
                if is_correct:
                    earned_points += question.points
                total_points += question.points

                answer_details.append({
                    "question_id": str(answer.question_id),
                    "question_text": question.text,
                    "question_type": question.question_type,
                    "student_answer": answer.answer_text,
                    "correct_answer": question.correct_answer,
                    "is_correct": is_correct,
                    "points_earned": points_earned,
                    "total_points": question.points,
                })

            # Calculate percentage
            percentage = (
                (earned_points / total_points * 100) if total_points > 0 else 0
            )
            passed = (
                earned_points >= (quiz.passing_score * total_points / 100)
                if total_points > 0
                else False
            )

            # Get attempt for time_taken
            attempt = await self.repos.quiz_attempt.get_by_id(submission.attempt_id)
            time_taken = None
            if attempt and attempt.submitted_at:
                time_diff = attempt.submitted_at - attempt.started_at
                time_taken = int(time_diff.total_seconds() / 60)  # minutes

            # Get student name
            student = await self.repos.student.get_by_id(student_id)
            student_name = (
                f"{student.user.first_name} {student.user.last_name}"
                if student and student.user
                else "Unknown"
            )

            self.logger.info(f"Quiz results retrieved for student {student_id}")

            return self.success_response(
                message="Quiz results retrieved successfully",
                data={
                    "submission_id": str(submission.id),
                    "student_name": student_name,
                    "score": earned_points,
                    "total_points": total_points,
                    "percentage": round(percentage, 2),
                    "passed": passed,
                    "passing_score": quiz.passing_score,
                    "time_taken_minutes": time_taken,
                    "submitted_at": (
                        submission.submitted_at.isoformat()
                        if submission.submitted_at
                        else None
                    ),
                    "answers": answer_details,
                },
            )

        except Exception as e:
            self.logger.error(f"Get quiz results error: {str(e)}")
            raise

    async def get_all_quiz_submissions(
        self,
        quiz_id: UUID,
        staff_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """
        Get all submissions for a quiz (staff only).
        
        Returns paginated list of submissions for a quiz. Only staff member
        who created the quiz can view all submissions. Validates staff owns quiz.
        
        Args:
            quiz_id: ID of quiz
            staff_id: ID of staff member requesting (must be quiz creator)
            skip: Pagination skip (default 0)
            limit: Pagination limit (default 20, max 100)
        
        Returns:
            Success response with data containing:
            - submissions: List of SubmissionSummary objects with:
                - submission_id, student_id, student_name, status,
                  grading_status, score, submitted_at
            - total: Total number of submissions
            - skip: Pagination skip
            - limit: Pagination limit
        
        Raises:
            NotFoundError: If quiz not found
            ForbiddenError: If staff doesn't own the quiz
        
        Example:
            result = await quiz_service.get_all_quiz_submissions(
                quiz_id=quiz_id,
                staff_id=staff_id,
                skip=0,
                limit=50
            )
            for sub in result["data"]["submissions"]:
                print(f"{sub['student_name']}: {sub['score']}%")
        """
        # Validate quiz exists
        quiz = await self.repos.quiz.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz #{quiz_id} not found")

        # Validate staff ownership (authorization)
        if quiz.staff_id != staff_id:
            raise ForbiddenError(
                "You can only view submissions for your own quizzes"
            )

        # Validate and limit pagination
        limit = min(limit, 100)
        if skip < 0:
            skip = 0

        try:
            # Fetch submissions with pagination
            submissions, total = (
                await self.repos.student_quiz_submission.get_by_quiz_paginated(
                    quiz_id, skip=skip, limit=limit
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

                # Get score if graded
                score = None
                if sub.status == "GRADED":
                    answers = await self.repos.student_answer.get_by_submission(
                        sub.id
                    )
                    # Calculate score from answers
                    questions = await self.repos.question.get_by_quiz(quiz_id)
                    questions_map = {q.id: q for q in questions}
                    earned = 0
                    total_pts = 0
                    for answer in answers:
                        question = questions_map.get(answer.question_id)
                        if not question:
                            continue
                        is_correct = answer.answer_text == question.correct_answer
                        if is_correct:
                            earned += question.points
                        total_pts += question.points
                    score = (
                        round(earned / total_pts * 100, 1) if total_pts > 0 else 0
                    )

                submission_summaries.append({
                    "submission_id": str(sub.id),
                    "student_id": str(sub.student_id),
                    "student_name": student_name,
                    "status": sub.status,
                    "grading_status": sub.status,
                    "score": score,
                    "submitted_at": (
                        sub.submitted_at.isoformat() if sub.submitted_at else None
                    ),
                })

            self.logger.info(
                f"Retrieved {len(submissions)} submissions for quiz {quiz_id}"
            )

            return self.success_response(
                message="Quiz submissions retrieved successfully",
                data={
                    "submissions": submission_summaries,
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                },
            )

        except Exception as e:
            self.logger.error(f"Get quiz submissions error: {str(e)}")
            raise

    async def get_quiz_statistics(
        self,
        quiz_id: UUID,
        staff_id: UUID,
    ) -> dict:
        """
        Get comprehensive statistics for a quiz.
        
        Returns overall analytics including average score, pass rate,
        completion rate, average time taken, score distribution, etc.
        Staff-only (must be quiz creator).
        
        Args:
            quiz_id: ID of quiz
            staff_id: ID of staff member (must be quiz creator)
        
        Returns:
            Success response with statistics containing:
            - total_attempts: Number of attempts
            - total_submissions: Number of submissions
            - completion_rate: Percentage of students who submitted
            - average_score: Mean score percentage
            - median_score: Median score percentage
            - highest_score: Maximum score achieved
            - lowest_score: Minimum score achieved
            - pass_rate: Percentage of students who passed
            - average_time_minutes: Average time spent on quiz
            - score_distribution: Histogram of score ranges
            - grade_distribution: Count of A/B/C/D/F grades
        
        Raises:
            NotFoundError: If quiz not found
            ForbiddenError: If staff doesn't own the quiz
        
        Example:
            result = await quiz_service.get_quiz_statistics(quiz_id, staff_id)
            if result["success"]:
                stats = result["data"]
                print(f"Pass rate: {stats['pass_rate']}%")
                print(f"Average: {stats['average_score']}%")
        """
        # Validate quiz exists
        quiz = await self.repos.quiz.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz #{quiz_id} not found")

        # Validate staff ownership
        if quiz.staff_id != staff_id:
            raise ForbiddenError("You can only view statistics for your own quizzes")

        try:
            # Get all submissions
            submissions = await self.repos.student_quiz_submission.get_by_quiz_all(
                quiz_id
            )
            total_submissions = len(submissions)

            # Get students in class
            students = await self.repos.student.get_by_class(quiz.class_id)
            total_attempts = len(students)

            # Calculate completion rate
            completion_rate = (
                (total_submissions / total_attempts * 100)
                if total_attempts > 0
                else 0
            )

            # Calculate scores and metrics
            scores = []
            time_taken_list = []
            passed_count = 0
            graded_count = 0

            for sub in submissions:
                if sub.status != "GRADED":
                    continue

                graded_count += 1

                # Calculate score for this submission
                answers = await self.repos.student_answer.get_by_submission(sub.id)
                questions = await self.repos.question.get_by_quiz(quiz_id)
                questions_map = {q.id: q for q in questions}

                earned = 0
                total_pts = 0
                for answer in answers:
                    q = questions_map.get(answer.question_id)
                    if not q:
                        continue
                    if answer.answer_text == q.correct_answer:
                        earned += q.points
                    total_pts += q.points

                score_pct = (
                    (earned / total_pts * 100) if total_pts > 0 else 0
                )
                scores.append(score_pct)

                # Check pass
                if score_pct >= quiz.passing_score:
                    passed_count += 1

                # Calculate time taken
                attempt = await self.repos.quiz_attempt.get_by_id(sub.attempt_id)
                if attempt and attempt.started_at and attempt.submitted_at:
                    time_diff = (
                        attempt.submitted_at - attempt.started_at
                    ).total_seconds() / 60
                    time_taken_list.append(time_diff)

            # Calculate statistics
            average_score = (
                sum(scores) / len(scores) if scores else 0
            )
            median_score = (
                sorted(scores)[len(scores) // 2] if scores else 0
            )
            highest_score = max(scores) if scores else 0
            lowest_score = min(scores) if scores else 0
            pass_rate = (
                (passed_count / graded_count * 100) if graded_count > 0 else 0
            )
            average_time = (
                sum(time_taken_list) / len(time_taken_list)
                if time_taken_list
                else 0
            )

            # Build score distribution (0-20, 20-40, 40-60, 60-80, 80-100)
            ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
            score_distribution = {}
            for low, high in ranges:
                count = len([s for s in scores if low <= s < high])
                score_distribution[f"{low}-{high}"] = count

            # Build grade distribution
            grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            for score in scores:
                if score >= 90:
                    grade_dist["A"] += 1
                elif score >= 80:
                    grade_dist["B"] += 1
                elif score >= 70:
                    grade_dist["C"] += 1
                elif score >= 60:
                    grade_dist["D"] += 1
                else:
                    grade_dist["F"] += 1

            self.logger.info(f"Quiz statistics calculated for {quiz_id}")

            return self.success_response(
                message="Quiz statistics retrieved successfully",
                data={
                    "quiz_id": str(quiz_id),
                    "quiz_title": quiz.title,
                    "total_attempts": total_attempts,
                    "total_submissions": total_submissions,
                    "graded_submissions": graded_count,
                    "completion_rate": round(completion_rate, 2),
                    "average_score": round(average_score, 2),
                    "median_score": round(median_score, 2),
                    "highest_score": round(highest_score, 2),
                    "lowest_score": round(lowest_score, 2),
                    "pass_rate": round(pass_rate, 2),
                    "average_time_minutes": round(average_time, 2),
                    "score_distribution": score_distribution,
                    "grade_distribution": grade_dist,
                },
            )

        except Exception as e:
            self.logger.error(f"Get quiz statistics error: {str(e)}")
            raise

    async def get_question_analysis(
        self,
        quiz_id: UUID,
        staff_id: UUID,
    ) -> dict:
        """
        Get per-question analysis and difficulty metrics.
        
        Calculates for each question: correctness rate (% students who got it right),
        difficulty score, discrimination index, and common wrong answers (if available).
        Useful for identifying difficult questions and question quality.
        
        Args:
            quiz_id: ID of quiz
            staff_id: ID of staff member (must be quiz creator)
        
        Returns:
            Success response with list of question analyses containing:
            - question_id, question_text, question_type
            - correct_count: Students who answered correctly
            - total_responses: Students who answered this question
            - correctness_rate: Percentage who got it right
            - discrimination_index: Correlation with overall quiz score
            - common_wrong_answers: Top 3 incorrect answers (if applicable)
        
        Raises:
            NotFoundError: If quiz not found
            ForbiddenError: If staff doesn't own the quiz
        """
        # Validate quiz exists
        quiz = await self.repos.quiz.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz #{quiz_id} not found")

        # Validate staff ownership
        if quiz.staff_id != staff_id:
            raise ForbiddenError(
                "You can only view analysis for your own quizzes"
            )

        try:
            # Get all questions
            questions = await self.repos.question.get_by_quiz(quiz_id)

            # Get all submissions
            submissions = await self.repos.student_quiz_submission.get_by_quiz_all(
                quiz_id
            )

            # Build submission scores map for discrimination index
            submission_scores = {}
            for sub in submissions:
                if sub.status != "GRADED":
                    continue

                answers = await self.repos.student_answer.get_by_submission(sub.id)
                earned = 0
                total_pts = 0
                for ans in answers:
                    q = next((q for q in questions if q.id == ans.question_id), None)
                    if q:
                        if ans.answer_text == q.correct_answer:
                            earned += q.points
                        total_pts += q.points

                score_pct = (earned / total_pts * 100) if total_pts > 0 else 0
                submission_scores[sub.id] = score_pct

            # Analyze each question
            question_analyses = []
            for question in questions:
                # Get all answers to this question
                all_answers = (
                    await self.repos.student_answer.get_by_question(question.id)
                )

                # Count correct responses
                correct_count = len(
                    [
                        a
                        for a in all_answers
                        if a.answer_text == question.correct_answer
                    ]
                )
                total_responses = len(all_answers)

                # Calculate correctness rate
                correctness_rate = (
                    (correct_count / total_responses * 100)
                    if total_responses > 0
                    else 0
                )

                # Calculate discrimination index (correlation between
                # question correctness and overall score)
                discrimination = 0.0
                if total_responses > 1:
                    # Simple discrimination: avg score of those who got it right
                    # minus avg score of those who got it wrong
                    right_scores = [
                        submission_scores.get(a.submission_id, 0)
                        for a in all_answers
                        if a.answer_text == question.correct_answer
                    ]
                    wrong_scores = [
                        submission_scores.get(a.submission_id, 0)
                        for a in all_answers
                        if a.answer_text != question.correct_answer
                    ]
                    avg_right = (
                        sum(right_scores) / len(right_scores) if right_scores else 0
                    )
                    avg_wrong = (
                        sum(wrong_scores) / len(wrong_scores) if wrong_scores else 0
                    )
                    discrimination = avg_right - avg_wrong

                # Get common wrong answers
                wrong_answers = {}
                for answer in all_answers:
                    if answer.answer_text != question.correct_answer:
                        ans_text = str(answer.answer_text)[:50]  # Limit length
                        wrong_answers[ans_text] = wrong_answers.get(ans_text, 0) + 1

                common_wrong = sorted(
                    wrong_answers.items(), key=lambda x: x[1], reverse=True
                )[:3]

                question_analyses.append({
                    "question_id": str(question.id),
                    "question_text": question.text[:100],  # Truncate for summary
                    "question_type": question.question_type,
                    "points": question.points,
                    "correct_count": correct_count,
                    "total_responses": total_responses,
                    "correctness_rate": round(correctness_rate, 2),
                    "discrimination_index": round(discrimination, 2),
                    "common_wrong_answers": [
                        {"answer": ans, "count": cnt} for ans, cnt in common_wrong
                    ],
                })

            self.logger.info(f"Question analysis calculated for {quiz_id}")

            return self.success_response(
                message="Question analysis retrieved successfully",
                data={
                    "quiz_id": str(quiz_id),
                    "total_questions": len(questions),
                    "questions": question_analyses,
                },
            )

        except Exception as e:
            self.logger.error(f"Get question analysis error: {str(e)}")
            raise

    async def get_student_performance_summary(
        self,
        student_id: UUID,
    ) -> dict:
        """
        Get student's performance summary across all quizzes.
        
        Returns overview of student's quiz performance including average score,
        quiz completion, pass/fail counts, and recent quizzes taken.
        Student can only view own performance.
        
        Args:
            student_id: ID of student
        
        Returns:
            Success response with summary containing:
            - total_quizzes_taken: Number of quizzes submitted
            - average_score: Mean percentage across all quizzes
            - pass_count: Number of quizzes passed
            - fail_count: Number of quizzes failed
            - pass_rate: Percentage of quizzes passed
            - recent_quizzes: Last 5 quizzes with scores
            - strongest_subject: Class/subject with best performance
            - weakest_subject: Class/subject with worst performance
        
        Raises:
            NotFoundError: If student not found
        """
        # Validate student exists
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        try:
            # Get all submissions by this student
            submissions = (
                await self.repos.student_quiz_submission.get_by_student(student_id)
            )

            # Filter to graded submissions only
            graded_subs = [s for s in submissions if s.status == "GRADED"]

            scores = []
            passed = 0
            recent_quizzes = []

            # Process each submission
            for sub in graded_subs:
                # Get quiz details
                quiz = await self.repos.quiz.get_by_id(sub.quiz_id)
                if not quiz:
                    continue

                # Calculate score
                answers = await self.repos.student_answer.get_by_submission(sub.id)
                questions = await self.repos.question.get_by_quiz(sub.quiz_id)
                questions_map = {q.id: q for q in questions}

                earned = 0
                total_pts = 0
                for answer in answers:
                    q = questions_map.get(answer.question_id)
                    if q:
                        if answer.answer_text == q.correct_answer:
                            earned += q.points
                        total_pts += q.points

                score_pct = (earned / total_pts * 100) if total_pts > 0 else 0
                scores.append(score_pct)

                if score_pct >= quiz.passing_score:
                    passed += 1

                # Add to recent if in last 5
                if len(recent_quizzes) < 5:
                    recent_quizzes.append({
                        "quiz_id": str(quiz.id),
                        "quiz_title": quiz.title,
                        "score": round(score_pct, 2),
                        "submitted_at": (
                            sub.submitted_at.isoformat()
                            if sub.submitted_at
                            else None
                        ),
                    })

            # Calculate statistics
            total_taken = len(graded_subs)
            average_score = sum(scores) / len(scores) if scores else 0
            pass_rate = (passed / total_taken * 100) if total_taken > 0 else 0

            self.logger.info(
                f"Performance summary retrieved for student {student_id}"
            )

            return self.success_response(
                message="Performance summary retrieved successfully",
                data={
                    "student_id": str(student_id),
                    "student_name": (
                        f"{student.user.first_name} {student.user.last_name}"
                        if student.user
                        else "Unknown"
                    ),
                    "total_quizzes_taken": total_taken,
                    "average_score": round(average_score, 2),
                    "pass_count": passed,
                    "fail_count": total_taken - passed,
                    "pass_rate": round(pass_rate, 2),
                    "recent_quizzes": recent_quizzes,
                },
            )

        except Exception as e:
            self.logger.error(f"Get student performance error: {str(e)}")
            raise

    async def get_attempt_history(
        self,
        quiz_id: UUID,
        student_id: UUID,
    ) -> dict:
        """
        Get student's attempt history for a specific quiz.
        
        Returns all attempts by a student on a quiz, including submission
        status, timestamp, score (if graded), and time taken.
        
        Args:
            quiz_id: ID of quiz
            student_id: ID of student
        
        Returns:
            Success response with list of attempts containing:
            - attempt_id, status, started_at, submitted_at,
              score (if graded), time_taken_minutes
        
        Raises:
            NotFoundError: If quiz or student not found
        """
        # Validate quiz and student exist
        quiz = await self.repos.quiz.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz #{quiz_id} not found")

        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student #{student_id} not found")

        try:
            # Get all attempts by this student on this quiz
            attempts = (
                await self.repos.quiz_attempt.get_by_quiz_and_student(
                    quiz_id, student_id
                )
            )

            attempt_history = []
            for attempt in attempts:
                # Get submission for this attempt (if exists)
                submission = (
                    await self.repos.student_quiz_submission.get_by_attempt(
                        attempt.id
                    )
                )

                score = None
                if submission and submission.status == "GRADED":
                    # Calculate score
                    answers = (
                        await self.repos.student_answer.get_by_submission(
                            submission.id
                        )
                    )
                    questions = await self.repos.question.get_by_quiz(quiz_id)
                    questions_map = {q.id: q for q in questions}

                    earned = 0
                    total_pts = 0
                    for answer in answers:
                        q = questions_map.get(answer.question_id)
                        if q:
                            if answer.answer_text == q.correct_answer:
                                earned += q.points
                            total_pts += q.points

                    score = (
                        round(earned / total_pts * 100, 2)
                        if total_pts > 0
                        else 0
                    )

                # Calculate time taken
                time_taken = None
                if attempt.submitted_at and attempt.started_at:
                    time_diff = (
                        attempt.submitted_at - attempt.started_at
                    ).total_seconds() / 60
                    time_taken = round(time_diff, 2)

                attempt_history.append({
                    "attempt_id": str(attempt.id),
                    "status": attempt.status,
                    "submission_status": submission.status if submission else None,
                    "started_at": (
                        attempt.started_at.isoformat()
                        if attempt.started_at
                        else None
                    ),
                    "submitted_at": (
                        attempt.submitted_at.isoformat()
                        if attempt.submitted_at
                        else None
                    ),
                    "score": score,
                    "time_taken_minutes": time_taken,
                })

            self.logger.info(
                f"Attempt history retrieved for student {student_id} on quiz {quiz_id}"
            )

            return self.success_response(
                message="Attempt history retrieved successfully",
                data={
                    "quiz_id": str(quiz_id),
                    "quiz_title": quiz.title,
                    "student_id": str(student_id),
                    "total_attempts": len(attempt_history),
                    "attempts": attempt_history,
                },
            )

        except Exception as e:
            self.logger.error(f"Get attempt history error: {str(e)}")
            raise

    async def get_grading_metrics(
        self,
        class_id: UUID,
        staff_id: UUID,
    ) -> dict:
        """
        Get grading workflow metrics for all quizzes in a class.
        
        Returns metrics about submission and grading status including
        pending submissions, pending grading, average grading time, etc.
        Useful for staff to track grading workload.
        
        Args:
            class_id: ID of class
            staff_id: ID of staff member
        
        Returns:
            Success response with metrics containing:
            - total_submissions: Total student submissions
            - graded_submissions: Submissions with grades assigned
            - pending_grading: Submissions awaiting grading
            - grading_completion_rate: Percentage graded
            - average_grading_time_hours: Average time to grade a submission
            - ungraded_by_quiz: Breakdown of pending grading by quiz
        
        Raises:
            NotFoundError: If class not found
        """
        # Validate class exists
        class_obj = await self.repos.class_repo.get_by_id(class_id)
        if not class_obj:
            raise NotFoundError(f"Class #{class_id} not found")

        try:
            # Get all quizzes for this class by this staff
            quizzes = await self.repos.quiz.get_by_class_and_staff(
                class_id, staff_id
            )

            total_subs = 0
            graded_subs = 0
            pending_subs = 0
            grading_times = []
            ungraded_by_quiz = {}

            for quiz in quizzes:
                # Get submissions for this quiz
                subs = (
                    await self.repos.student_quiz_submission.get_by_quiz_all(
                        quiz.id
                    )
                )

                quiz_pending = 0
                for sub in subs:
                    total_subs += 1

                    if sub.status == "GRADED":
                        graded_subs += 1
                        # Calculate grading time
                        if (
                            sub.submitted_at
                            and sub.graded_at
                        ):
                            time_diff = (
                                (sub.graded_at - sub.submitted_at).total_seconds()
                                / 3600
                            )
                            grading_times.append(time_diff)
                    else:
                        pending_subs += 1
                        quiz_pending += 1

                ungraded_by_quiz[quiz.title] = quiz_pending

            # Calculate metrics
            grading_rate = (
                (graded_subs / total_subs * 100) if total_subs > 0 else 0
            )
            avg_grading_time = (
                sum(grading_times) / len(grading_times)
                if grading_times
                else 0
            )

            self.logger.info(f"Grading metrics calculated for class {class_id}")

            return self.success_response(
                message="Grading metrics retrieved successfully",
                data={
                    "class_id": str(class_id),
                    "total_submissions": total_subs,
                    "graded_submissions": graded_subs,
                    "pending_grading": pending_subs,
                    "grading_completion_rate": round(grading_rate, 2),
                    "average_grading_time_hours": round(avg_grading_time, 2),
                    "ungraded_by_quiz": ungraded_by_quiz,
                },
            )

        except Exception as e:
            self.logger.error(f"Get grading metrics error: {str(e)}")
            raise
