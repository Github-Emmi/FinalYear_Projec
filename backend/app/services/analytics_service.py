"""
Analytics Service - Provides comprehensive analytics and reporting capabilities.

Provides methods for:
- Quiz performance analysis by class and student
- Student performance tracking with trend analysis
- Class-wide statistics and aggregations
- Institution-level dashboards
- Student engagement scoring
- Performance prediction based on historical data
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
import logging
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np

from app.models import (
    Quiz,
    Student,
    QuizAttempt,
    StudentQuizSubmission,
    Assignment,
    AttendanceReport,
    SessionYear,
)
from app.utils.exceptions import NotFoundError, ValidationError
from app.services.base_service import BaseService
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)

# Engagement Score Weights
ENGAGEMENT_WEIGHTS = {
    "quiz_participation": 0.40,
    "assignment_submission": 0.30,
    "attendance": 0.20,
    "quiz_performance": 0.10,
}

# Performance Prediction Thresholds
GRADE_THRESHOLDS = {
    "A": (90, 100),
    "B": (80, 89),
    "C": (70, 79),
    "D": (60, 69),
    "F": (0, 59),
}


class AnalyticsService(BaseService):
    """
    Service for comprehensive analytics, reporting, and performance prediction.

    Aggregates data across quizzes, assignments, and attendance to provide
    insights for students, classes, and institution-wide dashboards.
    Includes trend analysis, engagement scoring, and performance prediction.
    """

    def __init__(self, session: AsyncSession, repos: RepositoryFactory):
        """Initialize AnalyticsService with database session and repositories."""
        super().__init__(None, session, repos)
        self.logger = logger

    async def get_quiz_performance_report(
        self, class_id: UUID, session_year_id: Optional[UUID] = None
    ) -> dict:
        """
        Generate comprehensive quiz performance report for a class.

        Args:
            class_id: UUID of class
            session_year_id: Optional UUID of session (uses current if not provided)

        Returns:
            {
                total_quizzes,
                session,
                quizzes: [{
                    quiz_id,
                    quiz_name,
                    avg_score,
                    pass_rate,
                    total_attempts,
                    top_scorer: {name, score, percentage},
                    low_scorer: {name, score, percentage}
                }]
            }

        Raises:
            NotFoundError: If class or session not found
        """
        try:
            # Get current session if not provided
            if not session_year_id:
                current_session = await self.repos.session_year.get_current()
                if not current_session:
                    raise NotFoundError("No active session year")
                session_year_id = current_session.id

            # Validate class exists
            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            session = await self.repos.session_year.get_by_id(session_year_id)
            if not session:
                raise NotFoundError(f"Session {session_year_id} not found")

            # Get all quizzes assigned to this class
            quizzes = await self.repos.quiz.get_by_class(class_id)

            quiz_reports = []
            for quiz in quizzes:
                # Get all submissions for this quiz
                submissions = (
                    await self.repos.student_quiz_submission.get_by_quiz(quiz.id)
                )

                if not submissions:
                    continue

                # Calculate scores
                scores = [s.score for s in submissions if s.score is not None]
                if not scores:
                    continue

                avg_score = statistics.mean(scores)
                total_attempts = len(submissions)

                # Calculate pass rate (assuming 60% passing)
                pass_threshold = quiz.max_score * 0.6
                pass_count = sum(1 for s in submissions if s.score >= pass_threshold)
                pass_rate = (pass_count / total_attempts) * 100 if total_attempts > 0 else 0

                # Get top and low scorers
                sorted_submissions = sorted(
                    submissions, key=lambda x: x.score or 0, reverse=True
                )
                top_scorer = sorted_submissions[0] if sorted_submissions else None
                low_scorer = sorted_submissions[-1] if sorted_submissions else None

                top_scorer_data = None
                if top_scorer:
                    top_score_pct = (top_scorer.score / quiz.max_score) * 100 if quiz.max_score > 0 else 0
                    top_scorer_data = {
                        "student_id": str(top_scorer.student_id),
                        "student_name": top_scorer.student.user.first_name + " " + top_scorer.student.user.last_name,
                        "score": float(top_scorer.score),
                        "percentage": round(top_score_pct, 2),
                    }

                low_scorer_data = None
                if low_scorer:
                    low_score_pct = (low_scorer.score / quiz.max_score) * 100 if quiz.max_score > 0 else 0
                    low_scorer_data = {
                        "student_id": str(low_scorer.student_id),
                        "student_name": low_scorer.student.user.first_name + " " + low_scorer.student.user.last_name,
                        "score": float(low_scorer.score),
                        "percentage": round(low_score_pct, 2),
                    }

                quiz_reports.append(
                    {
                        "quiz_id": str(quiz.id),
                        "quiz_name": quiz.title,
                        "subject": quiz.subject.name if quiz.subject else None,
                        "avg_score": round(avg_score, 2),
                        "max_score": quiz.max_score,
                        "pass_rate": round(pass_rate, 2),
                        "total_attempts": total_attempts,
                        "top_scorer": top_scorer_data,
                        "low_scorer": low_scorer_data,
                    }
                )

            return self.success_response(
                data={
                    "class_id": str(class_id),
                    "class_name": cls.name,
                    "session": session.name,
                    "total_quizzes": len(quiz_reports),
                    "quizzes": quiz_reports,
                    "generated_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error generating quiz performance report: {str(e)}")
            raise ValidationError(f"Failed to generate report: {str(e)}")

    async def get_student_performance(
        self, student_id: UUID, session_year_id: Optional[UUID] = None
    ) -> dict:
        """
        Generate comprehensive performance report for a student.

        Includes GPA, trends, subject performance, strengths, and weaknesses.

        Args:
            student_id: UUID of student
            session_year_id: Optional UUID of session (uses current if not provided)

        Returns:
            {
                student_id,
                student_name,
                gpa,
                gpa_trend: "IMPROVING" | "DECLINING" | "STABLE",
                subjects: [{subject_name, avg_score, trend}],
                strengths: [subject_list],
                weaknesses: [subject_list],
                recommended_focus_areas: [...]
            }

        Raises:
            NotFoundError: If student or session not found
        """
        try:
            # Get current session if not provided
            if not session_year_id:
                current_session = await self.repos.session_year.get_current()
                if not current_session:
                    raise NotFoundError("No active session year")
                session_year_id = current_session.id

            # Validate student exists
            student = await self.repos.student.get_by_id(student_id)
            if not student:
                raise NotFoundError(f"Student {student_id} not found")

            # Get student's quiz submissions for this session
            submissions = (
                await self.repos.student_quiz_submission.get_by_student_and_session(
                    student_id, session_year_id
                )
            )

            if not submissions:
                return self.success_response(
                    data={
                        "student_id": str(student_id),
                        "student_name": f"{student.user.first_name} {student.user.last_name}",
                        "gpa": 0.0,
                        "gpa_trend": "STABLE",
                        "subjects": [],
                        "strengths": [],
                        "weaknesses": [],
                        "recommended_focus_areas": [],
                    }
                )

            # Aggregate by subject
            subject_performance = {}
            all_scores = []

            for submission in submissions:
                if not submission.quiz or not submission.score:
                    continue

                all_scores.append(submission.score)
                subject_id = str(submission.quiz.subject_id) if submission.quiz.subject_id else "Unknown"
                subject_name = submission.quiz.subject.name if submission.quiz.subject else "Unknown"

                if subject_id not in subject_performance:
                    subject_performance[subject_id] = {
                        "subject_name": subject_name,
                        "scores": [],
                    }

                subject_performance[subject_id]["scores"].append(
                    (submission.score / submission.quiz.max_score) * 100
                    if submission.quiz.max_score > 0
                    else 0
                )

            # Get previous session data for trend comparison
            previous_session = await self.repos.session_year.get_previous(session_year_id)
            prev_gpa = 0.0
            if previous_session:
                prev_submissions = (
                    await self.repos.student_quiz_submission.get_by_student_and_session(
                        student_id, previous_session.id
                    )
                )
                if prev_submissions:
                    prev_scores = [
                        (s.score / s.quiz.max_score) * 100
                        for s in prev_submissions
                        if s.score and s.quiz and s.quiz.max_score > 0
                    ]
                    if prev_scores:
                        prev_gpa = statistics.mean(prev_scores)

            # Calculate current GPA
            current_gpa = (
                statistics.mean(all_scores) / 100 * 4.0
                if all_scores
                else 0.0
            )

            # Determine GPA trend
            if prev_gpa == 0:
                gpa_trend = "STABLE"
            elif current_gpa > prev_gpa:
                gpa_trend = "IMPROVING"
            elif current_gpa < prev_gpa:
                gpa_trend = "DECLINING"
            else:
                gpa_trend = "STABLE"

            # Calculate subject performance
            subjects_data = []
            subject_scores = {}
            for subject_id, data in subject_performance.items():
                avg_score = (
                    statistics.mean(data["scores"]) if data["scores"] else 0.0
                )
                subjects_data.append(
                    {
                        "subject_id": subject_id,
                        "subject_name": data["subject_name"],
                        "avg_score": round(avg_score, 2),
                    }
                )
                subject_scores[data["subject_name"]] = avg_score

            # Identify strengths (top 3 subjects)
            sorted_subjects = sorted(subject_scores.items(), key=lambda x: x[1], reverse=True)
            strengths = [s[0] for s in sorted_subjects[:3]]
            weaknesses = [s[0] for s in sorted_subjects[-3:]]

            # Recommended focus areas (lowest scoring subjects)
            recommended_areas = weaknesses

            return self.success_response(
                data={
                    "student_id": str(student_id),
                    "student_name": f"{student.user.first_name} {student.user.last_name}",
                    "gpa": round(current_gpa, 2),
                    "gpa_trend": gpa_trend,
                    "subjects": subjects_data,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "recommended_focus_areas": recommended_areas,
                    "session": (await self.repos.session_year.get_by_id(session_year_id)).name,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error generating student performance: {str(e)}")
            raise ValidationError(f"Failed to generate performance report: {str(e)}")

    async def get_class_statistics(
        self, class_id: UUID, session_year_id: Optional[UUID] = None
    ) -> dict:
        """
        Generate comprehensive statistics for a class.

        Args:
            class_id: UUID of class
            session_year_id: Optional UUID of session (uses current if not provided)

        Returns:
            {
                class_name,
                total_students,
                avg_gpa,
                gpa_std_dev,
                attendance_rate,
                pass_rate,
                top_performers: [...],
                at_risk_students: [...],
                subject_performance: [...]
            }

        Raises:
            NotFoundError: If class or session not found
        """
        try:
            # Get current session if not provided
            if not session_year_id:
                current_session = await self.repos.session_year.get_current()
                if not current_session:
                    raise NotFoundError("No active session year")
                session_year_id = current_session.id

            # Validate class exists
            cls = await self.repos.class_.get_by_id(class_id)
            if not cls:
                raise NotFoundError(f"Class {class_id} not found")

            # Get all students in class
            students = await self.repos.student.get_by_class(class_id)

            # Calculate metrics for each student
            student_gpas = []
            attendance_rates = []
            pass_count = 0
            top_performers = []
            at_risk_students = []

            for student in students:
                # Get student's GPA
                submissions = (
                    await self.repos.student_quiz_submission.get_by_student_and_session(
                        student.id, session_year_id
                    )
                )

                if submissions:
                    scores = [
                        (s.score / s.quiz.max_score) * 100
                        if s.score and s.quiz and s.quiz.max_score > 0
                        else 0
                        for s in submissions
                    ]
                    avg_score = statistics.mean(scores) if scores else 0
                    gpa = avg_score / 100 * 4.0
                    student_gpas.append(gpa)

                    if avg_score >= 60:
                        pass_count += 1
                    if avg_score >= 85:
                        top_performers.append({
                            "student_id": str(student.id),
                            "student_name": f"{student.user.first_name} {student.user.last_name}",
                            "gpa": round(gpa, 2),
                            "avg_score": round(avg_score, 2),
                        })
                    elif avg_score < 60:
                        at_risk_students.append({
                            "student_id": str(student.id),
                            "student_name": f"{student.user.first_name} {student.user.last_name}",
                            "gpa": round(gpa, 2),
                            "avg_score": round(avg_score, 2),
                        })
                else:
                    # No submissions yet
                    at_risk_students.append({
                        "student_id": str(student.id),
                        "student_name": f"{student.user.first_name} {student.user.last_name}",
                        "gpa": 0.0,
                        "avg_score": 0.0,
                    })

                # Get student's attendance rate
                attendance_records = (
                    await self.repos.attendance_report.get_by_student_and_session(
                        student.id, session_year_id
                    )
                )
                if attendance_records:
                    present_count = sum(1 for r in attendance_records if r.status in ["PRESENT", "EXCUSED"])
                    attendance_rate = (present_count / len(attendance_records)) * 100
                    attendance_rates.append(attendance_rate)

            # Calculate class statistics
            avg_gpa = (
                statistics.mean(student_gpas) if student_gpas else 0.0
            )
            gpa_std_dev = (
                statistics.stdev(student_gpas) if len(student_gpas) > 1 else 0.0
            )
            avg_attendance = (
                statistics.mean(attendance_rates) if attendance_rates else 0.0
            )
            pass_rate = (
                (pass_count / len(students)) * 100 if students else 0.0
            )

            # Get subject performance
            quizzes = await self.repos.quiz.get_by_class(class_id)
            subject_performance = {}
            for quiz in quizzes:
                submissions = await self.repos.student_quiz_submission.get_by_quiz(quiz.id)
                if submissions:
                    scores = [
                        (s.score / quiz.max_score) * 100
                        if s.score and quiz.max_score > 0
                        else 0
                        for s in submissions
                    ]
                    avg_subject_score = statistics.mean(scores) if scores else 0
                    subject_name = quiz.subject.name if quiz.subject else "Unknown"
                    subject_performance[subject_name] = round(avg_subject_score, 2)

            return self.success_response(
                data={
                    "class_id": str(class_id),
                    "class_name": cls.name,
                    "session": (await self.repos.session_year.get_by_id(session_year_id)).name,
                    "total_students": len(students),
                    "avg_gpa": round(avg_gpa, 2),
                    "gpa_std_dev": round(gpa_std_dev, 2),
                    "attendance_rate": round(avg_attendance, 2),
                    "pass_rate": round(pass_rate, 2),
                    "top_performers": top_performers[:10],  # Top 10
                    "at_risk_students": at_risk_students[:10],  # At-risk 10
                    "subject_performance": subject_performance,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error generating class statistics: {str(e)}")
            raise ValidationError(f"Failed to generate statistics: {str(e)}")

    async def get_institution_dashboard_summary(self) -> dict:
        """
        Generate institution-wide dashboard summary for admins.

        Returns:
            {
                total_students,
                total_staff,
                total_classes,
                avg_gpa,
                avg_attendance,
                total_quizzes,
                total_assignments,
                pass_rate,
                top_classes: [...],
                at_risk_classes: [...]
            }
        """
        try:
            # Get current session
            current_session = await self.repos.session_year.get_current()
            if not current_session:
                raise NotFoundError("No active session year")

            # Count total students and staff
            all_students = await self.repos.student.get_all()
            all_users = await self.repos.user.get_all()
            staff_count = sum(1 for u in all_users if u.role == "STAFF")

            # Get all classes
            all_classes = await self.repos.class_.get_all()

            # Calculate system-wide metrics
            class_gpas = []
            class_attendance_rates = []
            class_pass_rates = []
            top_classes = []
            at_risk_classes = []

            for cls in all_classes:
                students = await self.repos.student.get_by_class(cls.id)
                if not students:
                    continue

                student_scores = []
                attendance_scores = []
                pass_count = 0

                for student in students:
                    submissions = (
                        await self.repos.student_quiz_submission.get_by_student_and_session(
                            student.id, current_session.id
                        )
                    )
                    if submissions:
                        scores = [
                            (s.score / s.quiz.max_score) * 100
                            if s.score and s.quiz and s.quiz.max_score > 0
                            else 0
                            for s in submissions
                        ]
                        avg_score = statistics.mean(scores) if scores else 0
                        student_scores.append(avg_score)
                        if avg_score >= 60:
                            pass_count += 1

                    # Attendance
                    attendance_records = (
                        await self.repos.attendance_report.get_by_student_and_session(
                            student.id, current_session.id
                        )
                    )
                    if attendance_records:
                        present = sum(1 for r in attendance_records if r.status in ["PRESENT", "EXCUSED"])
                        attendance_scores.append((present / len(attendance_records)) * 100)

                if student_scores:
                    class_avg = statistics.mean(student_scores)
                    class_gpa = class_avg / 100 * 4.0
                    class_gpas.append(class_gpa)

                    if class_avg >= 75:
                        top_classes.append({
                            "class_id": str(cls.id),
                            "class_name": cls.name,
                            "avg_gpa": round(class_gpa, 2),
                            "avg_score": round(class_avg, 2),
                        })
                    elif class_avg < 60:
                        at_risk_classes.append({
                            "class_id": str(cls.id),
                            "class_name": cls.name,
                            "avg_gpa": round(class_gpa, 2),
                            "avg_score": round(class_avg, 2),
                        })

                if students:
                    class_pass_rate = (pass_count / len(students)) * 100
                    class_pass_rates.append(class_pass_rate)

                if attendance_scores:
                    class_attendance_rates.append(statistics.mean(attendance_scores))

            # Count quizzes and assignments
            all_quizzes = await self.repos.quiz.get_all()
            all_assignments = await self.repos.assignment.get_all()

            # Calculate institution-wide metrics
            institution_avg_gpa = (
                statistics.mean(class_gpas) if class_gpas else 0.0
            )
            institution_avg_attendance = (
                statistics.mean(class_attendance_rates)
                if class_attendance_rates
                else 0.0
            )
            institution_pass_rate = (
                statistics.mean(class_pass_rates) if class_pass_rates else 0.0
            )

            return self.success_response(
                data={
                    "session": current_session.name,
                    "total_students": len(all_students),
                    "total_staff": staff_count,
                    "total_classes": len(all_classes),
                    "avg_gpa": round(institution_avg_gpa, 2),
                    "avg_attendance": round(institution_avg_attendance, 2),
                    "total_quizzes": len(all_quizzes),
                    "total_assignments": len(all_assignments),
                    "pass_rate": round(institution_pass_rate, 2),
                    "top_classes": top_classes[:5],  # Top 5
                    "at_risk_classes": at_risk_classes[:5],  # At-risk 5
                    "generated_at": datetime.now().isoformat(),
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error generating institution dashboard: {str(e)}")
            raise ValidationError(f"Failed to generate dashboard: {str(e)}")

    async def get_student_engagement_score(self, student_id: UUID) -> dict:
        """
        Calculate engagement score for a student based on multiple factors.

        Scoring: quiz_participation (40%), assignment_submission (30%),
        attendance (20%), quiz_performance (10%)

        Args:
            student_id: UUID of student

        Returns:
            {
                engagement_score: 75.5,
                engagement_level: "HIGH" | "MEDIUM" | "LOW",
                components: {
                    quiz_participation_score,
                    assignment_submission_score,
                    attendance_score,
                    quiz_performance_score
                },
                recommendations: [...]
            }

        Raises:
            NotFoundError: If student not found
        """
        try:
            # Validate student exists
            student = await self.repos.student.get_by_id(student_id)
            if not student:
                raise NotFoundError(f"Student {student_id} not found")

            # Get current session
            current_session = await self.repos.session_year.get_current()
            if not current_session:
                raise NotFoundError("No active session year")

            # Component 1: Quiz Participation (40%)
            quiz_submissions = (
                await self.repos.student_quiz_submission.get_by_student_and_session(
                    student_id, current_session.id
                )
            )
            total_quizzes = len(await self.repos.quiz.get_all())
            quiz_participation_rate = (
                (len(quiz_submissions) / total_quizzes) * 100
                if total_quizzes > 0
                else 0
            )
            quiz_participation_score = min(quiz_participation_rate, 100)

            # Component 2: Assignment Submission (30%)
            assignments = await self.repos.assignment.get_by_session(current_session.id)
            submitted_count = 0
            for assignment in assignments:
                submission = (
                    await self.repos.assignment_submission.get_by_student_and_assignment(
                        student_id, assignment.id
                    )
                )
                if submission:
                    submitted_count += 1

            total_assignments = len(assignments)
            assignment_submission_rate = (
                (submitted_count / total_assignments) * 100
                if total_assignments > 0
                else 0
            )
            assignment_submission_score = min(assignment_submission_rate, 100)

            # Component 3: Attendance (20%)
            attendance_records = (
                await self.repos.attendance_report.get_by_student_and_session(
                    student_id, current_session.id
                )
            )
            if attendance_records:
                present_count = sum(
                    1 for r in attendance_records if r.status in ["PRESENT", "EXCUSED"]
                )
                attendance_score = (
                    (present_count / len(attendance_records)) * 100
                )
            else:
                attendance_score = 0

            # Component 4: Quiz Performance (10%)
            if quiz_submissions:
                performance_scores = [
                    (s.score / s.quiz.max_score) * 100
                    if s.score and s.quiz and s.quiz.max_score > 0
                    else 0
                    for s in quiz_submissions
                ]
                avg_performance = (
                    statistics.mean(performance_scores) if performance_scores else 0
                )
                quiz_performance_score = min(avg_performance, 100)
            else:
                quiz_performance_score = 0

            # Calculate weighted engagement score
            engagement_score = (
                (quiz_participation_score * ENGAGEMENT_WEIGHTS["quiz_participation"])
                + (assignment_submission_score * ENGAGEMENT_WEIGHTS["assignment_submission"])
                + (attendance_score * ENGAGEMENT_WEIGHTS["attendance"])
                + (quiz_performance_score * ENGAGEMENT_WEIGHTS["quiz_performance"])
            )

            # Determine engagement level
            if engagement_score >= 75:
                engagement_level = "HIGH"
            elif engagement_score >= 50:
                engagement_level = "MEDIUM"
            else:
                engagement_level = "LOW"

            # Generate recommendations
            recommendations = []
            if quiz_participation_score < 50:
                recommendations.append("Increase quiz participation")
            if assignment_submission_score < 50:
                recommendations.append("Submit assignments on time")
            if attendance_score < 75:
                recommendations.append("Improve class attendance")
            if quiz_performance_score < 60:
                recommendations.append("Focus on improving quiz scores")

            return self.success_response(
                data={
                    "student_id": str(student_id),
                    "engagement_score": round(engagement_score, 2),
                    "engagement_level": engagement_level,
                    "components": {
                        "quiz_participation_score": round(quiz_participation_score, 2),
                        "assignment_submission_score": round(assignment_submission_score, 2),
                        "attendance_score": round(attendance_score, 2),
                        "quiz_performance_score": round(quiz_performance_score, 2),
                    },
                    "recommendations": recommendations,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error calculating engagement score: {str(e)}")
            raise ValidationError(f"Failed to calculate engagement score: {str(e)}")

    async def predict_student_performance(
        self, student_id: UUID, subject_id: Optional[UUID] = None
    ) -> dict:
        """
        Predict student's likely future performance based on historical data.

        Uses simple linear regression on historical quiz scores.

        Args:
            student_id: UUID of student
            subject_id: Optional UUID of specific subject (None = overall)

        Returns:
            {
                predicted_grade: "A" | "B" | "C" | "D" | "F",
                confidence: 0.85,
                predicted_score: 87.5,
                factors: [positive_factors, negative_factors]
            }

        Raises:
            NotFoundError: If student not found
        """
        try:
            # Validate student exists
            student = await self.repos.student.get_by_id(student_id)
            if not student:
                raise NotFoundError(f"Student {student_id} not found")

            # Get student's historical quiz submissions
            all_submissions = await self.repos.student_quiz_submission.get_by_student(
                student_id
            )

            if not all_submissions or len(all_submissions) < 2:
                # Not enough data for prediction
                return self.success_response(
                    data={
                        "student_id": str(student_id),
                        "predicted_grade": "INSUFFICIENT_DATA",
                        "confidence": 0.0,
                        "predicted_score": 0.0,
                        "factors": ["Not enough quiz submissions for prediction"],
                    }
                )

            # Calculate percentage scores
            percentage_scores = [
                (s.score / s.quiz.max_score) * 100
                if s.score and s.quiz and s.quiz.max_score > 0
                else 0
                for s in all_submissions
            ]

            # Filter by subject if provided
            if subject_id:
                percentage_scores = [
                    (s.score / s.quiz.max_score) * 100
                    if s.score and s.quiz and s.quiz.max_score > 0 and s.quiz.subject_id == subject_id
                    else None
                    for s in all_submissions
                ]
                percentage_scores = [s for s in percentage_scores if s is not None]

            if not percentage_scores or len(percentage_scores) < 2:
                return self.success_response(
                    data={
                        "student_id": str(student_id),
                        "predicted_grade": "INSUFFICIENT_DATA",
                        "confidence": 0.0,
                        "predicted_score": 0.0,
                        "factors": ["Not enough data for subject-specific prediction"],
                    }
                )

            # Simple linear regression: predict next score
            x = np.arange(len(percentage_scores))
            y = np.array(percentage_scores)

            coefficients = np.polyfit(x, y, 1)
            predicted_score = coefficients[0] * (len(x)) + coefficients[1]
            predicted_score = min(max(predicted_score, 0), 100)

            # Calculate confidence based on variance
            if len(y) < 5:
                confidence = 0.6  # Low confidence with few data points
            else:
                variance = np.var(y)
                confidence = max(0.5, 1 - (variance / 1000))  # Normalize variance

            # Determine predicted grade
            predicted_grade = None
            for grade, (low, high) in GRADE_THRESHOLDS.items():
                if low <= predicted_score <= high:
                    predicted_grade = grade
                    break

            # Identify factors
            factors = []
            recent_avg = statistics.mean(percentage_scores[-3:]) if len(percentage_scores) >= 3 else percentage_scores[-1]
            overall_avg = statistics.mean(percentage_scores)

            if recent_avg > overall_avg:
                factors.append("Recent scores show improvement")
            elif recent_avg < overall_avg:
                factors.append("Recent performance declining")

            if overall_avg >= 80:
                factors.append("Consistently strong performance")
            elif overall_avg < 60:
                factors.append("Needs significant improvement")

            return self.success_response(
                data={
                    "student_id": str(student_id),
                    "predicted_grade": predicted_grade,
                    "predicted_score": round(predicted_score, 2),
                    "confidence": round(confidence, 2),
                    "factors": factors,
                }
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Error predicting student performance: {str(e)}")
            raise ValidationError(f"Failed to predict performance: {str(e)}")
