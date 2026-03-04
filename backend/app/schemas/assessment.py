"""
Assessment Schemas (Quiz, Questions, Submissions)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, computed_field
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal


class QuizCreate(BaseModel):
    """Create quiz (staff only)"""
    title: str = Field(..., min_length=5, max_length=255, description="Quiz title")
    instructions: Optional[str] = Field(None, max_length=2000, description="Quiz instructions")
    description: Optional[str] = Field(None, max_length=1000, description="Quiz description")
    
    subject_id: UUID = Field(..., description="Subject UUID")
    class_id: UUID = Field(..., description="Class UUID")
    department_id: UUID = Field(..., description="Department UUID")
    session_year_id: UUID = Field(..., description="Session year UUID")
    
    start_time: datetime = Field(..., description="Quiz start time")
    end_time: datetime = Field(..., description="Quiz end time")
    deadline: datetime = Field(..., description="Last submission deadline")
    
    duration_minutes: int = Field(..., ge=15, le=180, description="Quiz duration in minutes")
    passing_score: float = Field(50.0, ge=0, le=100, description="Passing score percentage")
    
    @field_validator('end_time')
    @classmethod
    def validate_times(cls, v, info):
        """Ensure end_time > start_time"""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    @field_validator('deadline')
    @classmethod
    def validate_deadline(cls, v, info):
        """Ensure deadline >= end_time"""
        if 'end_time' in info.data and v < info.data['end_time']:
            raise ValueError('deadline must be after end_time')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Midterm Mathematics Exam",
            "instructions": "Answer all questions. No calculators allowed.",
            "subject_id": "550e8400-e29b-41d4-a716-446655440000",
            "class_id": "550e8400-e29b-41d4-a716-446655440001",
            "department_id": "550e8400-e29b-41d4-a716-446655440002",
            "session_year_id": "550e8400-e29b-41d4-a716-446655440003",
            "start_time": "2024-03-15T09:00:00",
            "end_time": "2024-03-15T10:00:00",
            "deadline": "2024-03-15T10:15:00",
            "duration_minutes": 60,
            "passing_score": 50.0
        }
    })


class QuizUpdate(BaseModel):
    """Update quiz (before publish)"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    instructions: Optional[str] = Field(None, max_length=2000)
    description: Optional[str] = Field(None, max_length=1000)
    passing_score: Optional[float] = Field(None, ge=0, le=100)
    duration_minutes: Optional[int] = Field(None, ge=15, le=180)


class QuizPublishRequest(BaseModel):
    """Publish/archivequiz"""
    status: Literal["DRAFT", "PUBLISHED", "ARCHIVED"] = Field(..., description="New status")


class QuizResponse(BaseModel):
    """Quiz response"""
    id: UUID
    title: str
    instructions: Optional[str]
    description: Optional[str]
    
    subject_id: UUID
    class_id: UUID
    department_id: UUID
    session_year_id: UUID
    staff_id: UUID
    
    start_time: datetime
    end_time: datetime
    deadline: datetime
    duration_minutes: int
    passing_score: float
    
    status: str  # DRAFT, PUBLISHED, ARCHIVED
    total_questions: int
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QuestionCreate(BaseModel):
    """Create quiz question"""
    quiz_id: UUID = Field(..., description="Quiz UUID")
    question_text: str = Field(..., min_length=10, description="Question text")
    question_type: Literal["MCQ", "SHORT_ANSWER", "ESSAY"] = Field(..., description="Question type")
    points: float = Field(1.0, ge=0.5, le=10, description="Points for this question")
    order: int = Field(0, ge=0, description="Question order")
    difficulty_level: Literal["EASY", "MEDIUM", "HARD"] = Field("MEDIUM", description="Difficulty")
    
    # MCQ options
    option_a: Optional[str] = Field(None, max_length=500)
    option_b: Optional[str] = Field(None, max_length=500)
    option_c: Optional[str] = Field(None, max_length=500)
    option_d: Optional[str] = Field(None, max_length=500)
    
    # Correct answer
    correct_answer: Optional[Literal["A", "B", "C", "D"]] = Field(None, description="Correct MCQ option")
    correct_text_answer: Optional[str] = Field(None, max_length=2000, description="Expected answer for short/essay")
    explanation: Optional[str] = Field(None, max_length=2000, description="Answer explanation")
    
    @field_validator('correct_answer')
    @classmethod
    def validate_mcq(cls, v, info):
        """If MCQ, all options and correct answer required"""
        if info.data.get('question_type') == 'MCQ':
            required_fields = ['option_a', 'option_b', 'option_c', 'option_d']
            for field in required_fields:
                if not info.data.get(field):
                    raise ValueError(f'MCQ requires all options (a, b, c, d) to be provided')
            if not v:
                raise ValueError('MCQ requires correct_answer to be specified')
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "quiz_id": "550e8400-e29b-41d4-a716-446655440000",
            "question_text": "What is 2 + 2?",
            "question_type": "MCQ",
            "points": 2.0,
            "order": 1,
            "difficulty_level": "EASY",
            "option_a": "3",
            "option_b": "4",
            "option_c": "5",
            "option_d": "6",
            "correct_answer": "B",
            "explanation": "2 + 2 equals 4"
        }
    })


class QuestionUpdate(BaseModel):
    """Update question"""
    question_text: Optional[str] = Field(None, min_length=10)
    points: Optional[float] = Field(None, ge=0.5, le=10)
    correct_answer: Optional[str] = None


class QuestionResponse(BaseModel):
    """Question response (without showing correct answer to students)"""
    id: UUID
    quiz_id: UUID
    question_text: str
    question_type: str
    points: float
    order: int
    difficulty_level: str
    
    # MCQ options
    option_a: Optional[str]
    option_b: Optional[str]
    option_c: Optional[str]
    option_d: Optional[str]
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class StudentAnswerCreate(BaseModel):
    """Submit single quiz answer"""
    question_id: UUID = Field(..., description="Question UUID")
    selected_option: Optional[str] = Field(None, max_length=1, description="MCQ option (A-D)")
    answer_text: Optional[str] = Field(None, max_length=5000, description="Short answer/essay text")


class StudentQuizSubmissionCreate(BaseModel):
    """Submit complete quiz"""
    quiz_id: UUID = Field(..., description="Quiz UUID")
    quiz_attempt_id: UUID = Field(..., description="Quiz attempt UUID")
    answers: list[StudentAnswerCreate] = Field(..., description="All answers")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "quiz_id": "550e8400-e29b-41d4-a716-446655440000",
            "quiz_attempt_id": "550e8400-e29b-41d4-a716-446655440001",
            "answers": [
                {
                    "question_id": "550e8400-e29b-41d4-a716-446655440002",
                    "selected_option": "B"
                }
            ]
        }
    })


class StudentQuizSubmissionResponse(BaseModel):
    """Submission response"""
    id: UUID
    student_id: UUID
    quiz_id: UUID
    
    submitted_at: datetime
    graded_at: Optional[datetime]
    
    total_score: float
    percentage: float
    
    @computed_field
    @property
    def is_passed(self) -> bool:
        """Check if score >= passing score"""
        return self.percentage >= 50.0  # Assuming 50% passing
    
    is_graded: bool
    feedback: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class QuizAttemptStartResponse(BaseModel):
    """Start quiz attempt - returns questions"""
    attempt_id: UUID
    quiz: QuizResponse
    questions: list[QuestionResponse]  # Without correct answers
    start_time: datetime
    end_time: datetime


class QuizAttemptResponse(BaseModel):
    """Quiz attempt status"""
    id: UUID
    student_id: UUID
    quiz_id: UUID
    
    started_at: datetime
    submitted_at: Optional[datetime]
    
    @computed_field
    @property
    def is_submitted(self) -> bool:
        return self.submitted_at is not None
    
    is_graded: bool
    
    model_config = ConfigDict(from_attributes=True)


class QuizResultsResponse(BaseModel):
    """Quiz results with detailed feedback"""
    submission_id: UUID
    quiz_id: UUID
    
    total_score: float
    percentage: float
    is_passed: bool
    
    answers: list[dict] = Field(..., description="Answer details with feedback")
    feedback: Optional[str]
    graded_at: datetime
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "submission_id": "550e8400-e29b-41d4-a716-446655440000",
            "quiz_id": "550e8400-e29b-41d4-a716-446655440001",
            "total_score": 15.0,
            "percentage": 75.0,
            "is_passed": True,
            "answers": [
                {
                    "question_id": "550e8400-e29b-41d4-a716-446655440002",
                    "student_answer": "B",
                    "correct_answer": "B",
                    "points_earned": 2.0,
                    "is_correct": True
                }
            ],
            "feedback": "Good performance! Review essay questions.",
            "graded_at": "2024-03-15T11:00:00"
        }
    })
