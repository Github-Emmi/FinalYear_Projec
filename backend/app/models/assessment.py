"""
Assessment models: Quiz, Question, StudentQuizSubmission, StudentAnswer
Assignment management: Assignment, AssignmentSubmission
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean, Integer, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
import uuid

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin


# ==================== QUIZ MODELS ====================

class Quiz(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Quiz/Exam configuration with questions, timing, and metadata.
    Can be in DRAFT or PUBLISHED status.
    """
    __tablename__ = "quiz"

    # Quiz metadata
    title = Column(String(255), nullable=False, index=True)
    instructions = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    # Academic linkage
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subject.id"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("class.id"), nullable=False, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("department.id"), nullable=False, index=True)
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=False, index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    deadline = Column(DateTime, nullable=False, index=True)  # Notify before this time
    duration_minutes = Column(Integer, default=30, nullable=False)
    
    # Status
    status = Column(String(20), default="DRAFT", nullable=False, index=True)  # DRAFT, PUBLISHED
    total_questions = Column(Integer, default=0, nullable=False)
    passing_score = Column(Float, default=50.0, nullable=False)  # Percentage
    
    # Relationships
    subject = relationship("Subject")
    class_obj = relationship("Class")
    department = relationship("Department")
    session_year = relationship("SessionYear")
    staff = relationship("CustomUser")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")
    submissions = relationship("StudentQuizSubmission", back_populates="quiz", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_quiz_subject_session", "subject_id", "session_year_id"),
        Index("ix_quiz_class_session", "class_id", "session_year_id"),
        Index("ix_quiz_status_deadline", "status", "deadline"),
    )

    def __str__(self):
        return self.title


class Question(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Single quiz question - MCQ or open-ended.
    Multiple questions per quiz.
    """
    __tablename__ = "question"

    QUESTION_TYPE_CHOICES = [
        ("MCQ", "Multiple Choice"),
        ("SHORT_ANSWER", "Short Answer"),
        ("ESSAY", "Essay (AI-Graded)"),
    ]

    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quiz.id"), nullable=False, index=True)
    
    # Question content
    question_text: Text = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False)  # MCQ, SHORT_ANSWER, ESSAY
    points = Column(Float, default=1.0, nullable=False)
    
    # MCQ Options (A-D)
    option_a = Column(String(500), nullable=True)
    option_b = Column(String(500), nullable=True)
    option_c = Column(String(500), nullable=True)
    option_d = Column(String(500), nullable=True)
    
    # Correct answer
    correct_answer = Column(String(1), nullable=True)  # A, B, C, D for MCQ
    correct_text_answer: Text = Column(Text, nullable=True)  # Expected answer for short/essay
    explanation: Text = Column(Text, nullable=True)  # Answer explanation
    
    # Metadata
    difficulty_level = Column(String(20), nullable=True)  # EASY, MEDIUM, HARD
    order = Column(Integer, default=0, nullable=False)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("StudentAnswer", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_question_quiz_order", "quiz_id", "order"),
    )

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"


class QuizAttempt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Student's single attempt at a quiz.
    Unique constraint: one attempt per student per quiz.
    """
    __tablename__ = "quiz_attempt"

    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quiz.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student.id"), nullable=False, index=True)
    
    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Scoring
    score = Column(Float, nullable=True)  # Raw score before percentage
    percentage = Column(Float, nullable=True)
    is_passed: Boolean = Column(Boolean, nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("Student", backref="quiz_attempts")

    __table_args__ = (
        UniqueConstraint("quiz_id", "student_id", name="uq_quiz_student_attempt"),
        Index("ix_quiz_attempt_student", "student_id"),
        Index("ix_quiz_attempt_status", "completed_at"),
    )

    def __str__(self):
        return f"{self.student.user.username} - {self.quiz.title}"


class StudentQuizSubmission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Student's complete quiz submission with all answers.
    Aggregates StudentAnswer records and scoring.
    """
    __tablename__ = "student_quiz_submission"

    # Links
    student_id = Column(UUID(as_uuid=True), ForeignKey("student.id"), nullable=False, index=True)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quiz.id"), nullable=False, index=True)
    
    # Submission metadata
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Grading
    total_score = Column(Float, default=0.0, nullable=False)
    percentage_score = Column(Float, nullable=True)
    is_graded: Boolean = Column(Boolean, default=False, nullable=False, index=True)
    graded_at = Column(DateTime, nullable=True)
    
    # Feedback
    feedback: Text = Column(Text, nullable=True)
    ai_used: Boolean = Column(Boolean, default=False, nullable=False)  # Was AI used for grading?
    
    # Relationships
    student = relationship("Student", backref="quiz_submissions")
    quiz = relationship("Quiz", back_populates="submissions")
    answers = relationship("StudentAnswer", back_populates="submission", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_quiz_submission_student", "student_id"),
        Index("ix_quiz_submission_graded", "is_graded"),
    )

    def __str__(self):
        return f"{self.student.user.username} - {self.quiz.title}"


class StudentAnswer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual answer to a quiz question.
    One per student per question per submission.
    """
    __tablename__ = "student_answer"

    # Links
    submission_id = Column(UUID(as_uuid=True), ForeignKey("student_quiz_submission.id"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("question.id"), nullable=False, index=True)
    
    # Student response
    selected_option = Column(String(1), nullable=True)  # A, B, C, D for MCQ
    text_answer: Text = Column(Text, nullable=True)  # For short answer/essay
    
    # Grading
    is_correct: Boolean = Column(Boolean, default=False, nullable=False)
    points_earned = Column(Float, default=0.0, nullable=False)
    ai_confidence = Column(Float, nullable=True)  # Confidence score if AI graded (0-1)
    
    # Relationships
    submission = relationship("StudentQuizSubmission", back_populates="answers")
    question = relationship("Question", back_populates="answers")

    __table_args__ = (
        UniqueConstraint("submission_id", "question_id", name="uq_answer_submission_question"),
        Index("ix_student_answer_correct", "is_correct"),
    )

    def __str__(self):
        return f"Answer to Q{self.question_id}"


# ==================== ASSIGNMENT MODELS ====================

class Assignment(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Assignment/Homework configuration.
    Created by staff, submitted by students.
    """
    __tablename__ = "assignment"

    # Metadata
    title = Column(String(255), nullable=False, index=True)
    description: Text = Column(Text, nullable=True)
    
    # Academic linkage
    class_id = Column(UUID(as_uuid=True), ForeignKey("class.id"), nullable=False, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("department.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subject.id"), nullable=False, index=True)
    session_year_id = Column(UUID(as_uuid=True), ForeignKey("session_year.id"), nullable=False, index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("custom_user.id"), nullable=False, index=True)
    
    # Document
    assignment_file = Column(String(500), nullable=True)  # Cloudinary URL
    
    # Timing
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False, index=True)
    
    # Grading
    total_marks = Column(Float, default=100.0, nullable=False)
    passing_marks = Column(Float, default=40.0, nullable=False)
    
    # Relationships
    class_obj = relationship("Class")
    department = relationship("Department")
    subject = relationship("Subject")
    session_year = relationship("SessionYear")
    staff = relationship("CustomUser")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_assignment_class_subject", "class_id", "subject_id"),
        Index("ix_assignment_due_date", "due_date"),
    )

    def __str__(self):
        return self.title

    def is_due(self) -> bool:
        """Check if assignment is overdue"""
        return datetime.utcnow() > self.due_date


class AssignmentSubmission(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditableMixin):
    """
    Student's assignment submission.
    Includes file, grading, and feedback.
    """
    __tablename__ = "assignment_submission"

    # Links
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignment.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student.id"), nullable=False, index=True)
    
    # Submission
    submitted_file = Column(String(500), nullable=False)  # Cloudinary URL
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Grading
    marks_obtained = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    grade_letter = Column(String(2), nullable=True)  # A, B, C, D, F
    is_graded: Boolean = Column(Boolean, default=False, nullable=False, index=True)
    graded_at = Column(DateTime, nullable=True)
    
    # Feedback
    feedback: Text = Column(Text, nullable=True)
    remarks: Text = Column(Text, nullable=True)
    
    # Status
    is_late: Boolean = Column(Boolean, default=False, nullable=False)
    late_days = Column(Integer, default=0, nullable=False)
    
    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student", backref="assignment_submissions")

    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student_submission"),
        Index("ix_assignment_submission_graded", "is_graded"),
        Index("ix_assignment_submission_student", "student_id"),
    )

    def __str__(self):
        return f"{self.student.user.username} - {self.assignment.title}"
