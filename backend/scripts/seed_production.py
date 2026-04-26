#!/usr/bin/env python
"""
Production seed script — bootstraps admin, staff, students, academic structure,
quizzes, and assignments in the live Render PostgreSQL database.

Usage (from backend/):
    export DATABASE_URL="postgresql://school_user:...@.../school_management_hhcg"
    python scripts/seed_production.py

Optional flags:
    --reset      Drop and re-insert all seed data (idempotent)
    --admin-only  Only create the super-admin user
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

# ── path bootstrap ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv
load_dotenv(_BACKEND / ".env")

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import hash_password
from app.models.academic import ClassRoom, Department, SessionYear, Subject
from app.models.assessment import (
    AttemptStatus,
    Question,
    QuestionType,
    Quiz,
    QuizAttempt,
    QuizResult,
    QuizStatus,
)
from app.models.assignment import Assignment, AssignmentStatus
from app.models.attendance import AttendanceSession
from app.models.staff import StaffProfile
from app.models.student import StudentProfile
from app.models.user import User, UserRole

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg: str)   -> None: print(f"{GREEN}  ✓  {RESET}{msg}")
def fail(msg: str) -> None: print(f"{RED}  ✗  {RESET}{msg}")
def info(msg: str) -> None: print(f"{CYAN}  ·  {RESET}{msg}")
def head(msg: str) -> None: print(f"\n{BOLD}{msg}{RESET}")


# ── helpers ───────────────────────────────────────────────────────────────────

async def user_exists(session: AsyncSession, username: str) -> bool:
    result = await session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none() is not None


async def get_or_create_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: UserRole,
) -> User:
    result = await session.execute(
        select(User).where(User.username == username)
    )
    existing = result.scalar_one_or_none()
    if existing:
        info(f"User already exists: {username}")
        return existing
    user = User(
        id=uuid.uuid4(),
        username=username,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role.value,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    ok(f"Created user: {username} ({role.value})")
    return user


async def get_or_create_department(
    session: AsyncSession, name: str
) -> Department:
    result = await session.execute(
        select(Department).where(Department.name == name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        info(f"Department exists: {name}")
        return existing
    dept = Department(id=uuid.uuid4(), name=name)
    session.add(dept)
    await session.flush()
    ok(f"Created department: {name}")
    return dept


async def get_or_create_session_year(
    session: AsyncSession, start: int, end: int, is_current: bool = False
) -> SessionYear:
    result = await session.execute(
        select(SessionYear).where(
            SessionYear.start_year == start,
            SessionYear.end_year == end,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        info(f"Session year exists: {start}/{end}")
        return existing
    sy = SessionYear(
        id=uuid.uuid4(),
        start_year=start,
        end_year=end,
        is_current=is_current,
    )
    session.add(sy)
    await session.flush()
    ok(f"Created session year: {start}/{end} (current={is_current})")
    return sy


async def get_or_create_classroom(
    session: AsyncSession, name: str, department: Department
) -> ClassRoom:
    result = await session.execute(
        select(ClassRoom).where(
            ClassRoom.name == name,
            ClassRoom.department_id == department.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        info(f"Classroom exists: {name}")
        return existing
    cr = ClassRoom(id=uuid.uuid4(), name=name, department_id=department.id)
    session.add(cr)
    await session.flush()
    ok(f"Created classroom: {name}")
    return cr


async def get_or_create_subject(
    session: AsyncSession,
    name: str,
    classroom: ClassRoom,
    staff_profile: StaffProfile,
) -> Subject:
    result = await session.execute(
        select(Subject).where(
            Subject.name == name,
            Subject.classroom_id == classroom.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        info(f"Subject exists: {name}")
        return existing
    subj = Subject(
        id=uuid.uuid4(),
        name=name,
        classroom_id=classroom.id,
        staff_id=staff_profile.id,
    )
    session.add(subj)
    await session.flush()
    ok(f"Created subject: {name}")
    return subj


# ── seed phases ───────────────────────────────────────────────────────────────

async def seed_admin(session: AsyncSession) -> User:
    head("Phase 1 — Admin User")
    return await get_or_create_user(
        session,
        username="admin",
        email="admin@school.edu",
        password="AdminPass123!",
        first_name="Super",
        last_name="Admin",
        role=UserRole.admin,
    )


async def seed_academic_structure(session: AsyncSession) -> dict:
    head("Phase 2 — Academic Structure")

    # ── departments ───────────────────────────────────────────────────────────
    dept_cs   = await get_or_create_department(session, "Computer Science")
    dept_math = await get_or_create_department(session, "Mathematics")
    dept_eng  = await get_or_create_department(session, "English Language")
    dept_sci  = await get_or_create_department(session, "General Science")

    # ── session year ──────────────────────────────────────────────────────────
    session_yr = await get_or_create_session_year(session, 2025, 2026, is_current=True)
    await get_or_create_session_year(session, 2024, 2025, is_current=False)

    # ── classrooms ────────────────────────────────────────────────────────────
    cs_yr1   = await get_or_create_classroom(session, "CS Year 1",   dept_cs)
    cs_yr2   = await get_or_create_classroom(session, "CS Year 2",   dept_cs)
    math_yr1 = await get_or_create_classroom(session, "Math Year 1", dept_math)
    eng_yr1  = await get_or_create_classroom(session, "Eng Year 1",  dept_eng)

    return {
        "departments": {
            "cs": dept_cs, "math": dept_math,
            "eng": dept_eng, "sci": dept_sci,
        },
        "session_year": session_yr,
        "classrooms": {
            "cs_yr1": cs_yr1, "cs_yr2": cs_yr2,
            "math_yr1": math_yr1, "eng_yr1": eng_yr1,
        },
    }


async def seed_staff(
    session: AsyncSession, academic: dict
) -> dict[str, StaffProfile]:
    head("Phase 3 — Staff Users & Profiles")

    staff_data = [
        # (username, email, first, last, dept_key, designation)
        ("staff.alice",  "alice@school.edu",   "Alice",  "Johnson",  "cs",   "Senior Lecturer"),
        ("staff.bob",    "bob@school.edu",     "Bob",    "Williams", "math", "Lecturer"),
        ("staff.carol",  "carol@school.edu",   "Carol",  "Brown",    "eng",  "Lecturer"),
        ("staff.david",  "david@school.edu",   "David",  "Taylor",   "cs",   "Lab Instructor"),
    ]

    profiles: dict[str, StaffProfile] = {}
    depts = academic["departments"]

    for username, email, first, last, dept_key, designation in staff_data:
        user = await get_or_create_user(
            session, username, email,
            password="StaffPass123!",
            first_name=first, last_name=last,
            role=UserRole.staff,
        )
        result = await session.execute(
            select(StaffProfile).where(StaffProfile.user_id == user.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            info(f"Staff profile exists: {username}")
            profiles[username] = existing
            continue
        profile = StaffProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            department_id=depts[dept_key].id,
            designation=designation,
            phone=f"+44700000{len(profiles):04d}",
        )
        session.add(profile)
        await session.flush()
        profiles[username] = profile
        ok(f"Created staff profile: {first} {last} → {designation}")

    return profiles


async def seed_subjects(
    session: AsyncSession,
    academic: dict,
    staff_profiles: dict[str, StaffProfile],
) -> dict[str, Subject]:
    head("Phase 4 — Subjects")

    classrooms = academic["classrooms"]
    subject_data = [
        # (name, classroom_key, staff_username)
        ("Introduction to Programming",  "cs_yr1",   "staff.alice"),
        ("Data Structures & Algorithms", "cs_yr2",   "staff.alice"),
        ("Web Development",              "cs_yr1",   "staff.david"),
        ("Database Systems",             "cs_yr2",   "staff.david"),
        ("Calculus I",                   "math_yr1", "staff.bob"),
        ("Linear Algebra",               "math_yr1", "staff.bob"),
        ("Academic Writing",             "eng_yr1",  "staff.carol"),
    ]

    subjects: dict[str, Subject] = {}
    for name, cr_key, staff_un in subject_data:
        subj = await get_or_create_subject(
            session,
            name=name,
            classroom=classrooms[cr_key],
            staff_profile=staff_profiles[staff_un],
        )
        subjects[name] = subj

    return subjects


async def seed_students(
    session: AsyncSession, academic: dict
) -> list[StudentProfile]:
    head("Phase 5 — Student Users & Profiles")

    session_yr = academic["session_year"]
    classrooms = academic["classrooms"]

    student_data = [
        # (username, email, first, last, classroom_key, roll)
        ("stu.emma",    "emma@students.edu",    "Emma",    "Smith",    "cs_yr1",   "CS25-001"),
        ("stu.liam",    "liam@students.edu",    "Liam",    "Jones",    "cs_yr1",   "CS25-002"),
        ("stu.olivia",  "olivia@students.edu",  "Olivia",  "Davis",    "cs_yr1",   "CS25-003"),
        ("stu.noah",    "noah@students.edu",    "Noah",    "Wilson",   "cs_yr1",   "CS25-004"),
        ("stu.ava",     "ava@students.edu",     "Ava",     "Moore",    "cs_yr2",   "CS24-001"),
        ("stu.ethan",   "ethan@students.edu",   "Ethan",   "Anderson", "cs_yr2",   "CS24-002"),
        ("stu.sophia",  "sophia@students.edu",  "Sophia",  "Martinez", "math_yr1", "MT25-001"),
        ("stu.mason",   "mason@students.edu",   "Mason",   "Taylor",   "math_yr1", "MT25-002"),
        ("stu.isabella","isabella@students.edu","Isabella","Thomas",   "eng_yr1",  "EN25-001"),
        ("stu.james",   "james@students.edu",   "James",   "Jackson",  "eng_yr1",  "EN25-002"),
    ]

    profiles: list[StudentProfile] = []
    for idx, (username, email, first, last, cr_key, roll) in enumerate(student_data):
        user = await get_or_create_user(
            session, username, email,
            password="StudPass123!",
            first_name=first, last_name=last,
            role=UserRole.student,
        )
        result = await session.execute(
            select(StudentProfile).where(StudentProfile.user_id == user.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            info(f"Student profile exists: {username}")
            profiles.append(existing)
            continue
        profile = StudentProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            classroom_id=classrooms[cr_key].id,
            session_year_id=session_yr.id,
            roll_number=roll,
            gender="female" if idx % 2 == 0 else "male",
            date_of_birth=date(2004 + (idx % 3), 1 + (idx % 12), 1 + (idx % 28)),
            phone=f"+44701000{idx:04d}",
            address="123 University Rd, London",
        )
        session.add(profile)
        await session.flush()
        profiles.append(profile)
        ok(f"Created student: {first} {last} ({roll})")

    return profiles


async def seed_quizzes(
    session: AsyncSession,
    subjects: dict[str, Subject],
    staff_profiles: dict[str, StaffProfile],
) -> list[Quiz]:
    head("Phase 6 — Quizzes & Questions")

    quiz_definitions = [
        {
            "title": "Python Basics Quiz",
            "description": "Fundamental Python concepts: variables, loops, functions.",
            "subject": "Introduction to Programming",
            "staff": "staff.alice",
            "status": QuizStatus.published,
            "time_limit_minutes": 30,
            "pass_score": 60.0,
            "ai_grading_enabled": True,
            "due_date": datetime.utcnow() + timedelta(days=14),
            "questions": [
                {
                    "text": "Which keyword is used to define a function in Python?",
                    "type": QuestionType.multiple_choice,
                    "option_a": "func",
                    "option_b": "def",
                    "option_c": "function",
                    "option_d": "define",
                    "correct_answer": "b",
                    "marks": 2.0,
                },
                {
                    "text": "Python lists are mutable.",
                    "type": QuestionType.true_false,
                    "correct_answer": "true",
                    "marks": 1.0,
                },
                {
                    "text": "What does the `len()` function return?",
                    "type": QuestionType.multiple_choice,
                    "option_a": "The data type of an object",
                    "option_b": "The memory address",
                    "option_c": "The number of items in an object",
                    "option_d": "The last element",
                    "correct_answer": "c",
                    "marks": 2.0,
                },
                {
                    "text": "Briefly explain what a list comprehension is and give one example.",
                    "type": QuestionType.short_answer,
                    "correct_answer": None,
                    "marks": 5.0,
                },
                {
                    "text": "Which of the following is NOT a valid Python data type?",
                    "type": QuestionType.multiple_choice,
                    "option_a": "int",
                    "option_b": "float",
                    "option_c": "char",
                    "option_d": "str",
                    "correct_answer": "c",
                    "marks": 2.0,
                },
            ],
        },
        {
            "title": "Data Structures Mid-Term",
            "description": "Arrays, linked lists, stacks, queues, and trees.",
            "subject": "Data Structures & Algorithms",
            "staff": "staff.alice",
            "status": QuizStatus.published,
            "time_limit_minutes": 60,
            "pass_score": 50.0,
            "ai_grading_enabled": True,
            "due_date": datetime.utcnow() + timedelta(days=7),
            "questions": [
                {
                    "text": "What is the time complexity of binary search?",
                    "type": QuestionType.multiple_choice,
                    "option_a": "O(n)",
                    "option_b": "O(n²)",
                    "option_c": "O(log n)",
                    "option_d": "O(1)",
                    "correct_answer": "c",
                    "marks": 3.0,
                },
                {
                    "text": "A stack follows LIFO (Last In, First Out) order.",
                    "type": QuestionType.true_false,
                    "correct_answer": "true",
                    "marks": 1.0,
                },
                {
                    "text": "Which data structure uses a 'rear' and a 'front' pointer?",
                    "type": QuestionType.multiple_choice,
                    "option_a": "Stack",
                    "option_b": "Queue",
                    "option_c": "Tree",
                    "option_d": "Graph",
                    "correct_answer": "b",
                    "marks": 2.0,
                },
                {
                    "text": "Compare and contrast a stack and a queue. Give a real-world use case for each.",
                    "type": QuestionType.short_answer,
                    "correct_answer": None,
                    "marks": 10.0,
                },
            ],
        },
        {
            "title": "Calculus I — Limits & Derivatives",
            "description": "Foundational calculus: limits, continuity, differentiation.",
            "subject": "Calculus I",
            "staff": "staff.bob",
            "status": QuizStatus.published,
            "time_limit_minutes": 45,
            "pass_score": 55.0,
            "ai_grading_enabled": False,
            "due_date": datetime.utcnow() + timedelta(days=21),
            "questions": [
                {
                    "text": "What is the derivative of x²?",
                    "type": QuestionType.multiple_choice,
                    "option_a": "x",
                    "option_b": "2x",
                    "option_c": "2",
                    "option_d": "x/2",
                    "correct_answer": "b",
                    "marks": 2.0,
                },
                {
                    "text": "The limit of 1/x as x approaches infinity is 0.",
                    "type": QuestionType.true_false,
                    "correct_answer": "true",
                    "marks": 1.0,
                },
                {
                    "text": "What is lim(x→0) sin(x)/x?",
                    "type": QuestionType.multiple_choice,
                    "option_a": "0",
                    "option_b": "∞",
                    "option_c": "1",
                    "option_d": "undefined",
                    "correct_answer": "c",
                    "marks": 3.0,
                },
            ],
        },
    ]

    created_quizzes: list[Quiz] = []

    for qd in quiz_definitions:
        subj = subjects.get(qd["subject"])
        if not subj:
            fail(f"Subject not found: {qd['subject']}")
            continue
        staff = staff_profiles.get(qd["staff"])
        if not staff:
            fail(f"Staff not found: {qd['staff']}")
            continue

        # Check if quiz already exists
        result = await session.execute(
            select(Quiz).where(
                Quiz.title == qd["title"],
                Quiz.subject_id == subj.id,
            )
        )
        existing_quiz = result.scalar_one_or_none()
        if existing_quiz:
            info(f"Quiz exists: {qd['title']}")
            created_quizzes.append(existing_quiz)
            continue

        quiz = Quiz(
            id=uuid.uuid4(),
            title=qd["title"],
            description=qd["description"],
            subject_id=subj.id,
            staff_id=staff.id,
            status=qd["status"].value,
            time_limit_minutes=qd["time_limit_minutes"],
            max_attempts=2,
            pass_score=qd["pass_score"],
            due_date=qd["due_date"],
            ai_grading_enabled=qd["ai_grading_enabled"],
        )
        session.add(quiz)
        await session.flush()

        for order, q_def in enumerate(qd["questions"]):
            question = Question(
                id=uuid.uuid4(),
                quiz_id=quiz.id,
                text=q_def["text"],
                question_type=q_def["type"].value,
                option_a=q_def.get("option_a"),
                option_b=q_def.get("option_b"),
                option_c=q_def.get("option_c"),
                option_d=q_def.get("option_d"),
                correct_answer=q_def.get("correct_answer"),
                marks=q_def["marks"],
                order=order,
            )
            session.add(question)

        await session.flush()
        created_quizzes.append(quiz)
        ok(f"Created quiz: {qd['title']} ({len(qd['questions'])} questions)")

    return created_quizzes


async def seed_assignments(
    session: AsyncSession,
    subjects: dict[str, Subject],
    staff_profiles: dict[str, StaffProfile],
) -> list[Assignment]:
    head("Phase 7 — Assignments")

    assignment_definitions = [
        {
            "title": "Assignment 1: Hello World & Variables",
            "description": (
                "Write a Python program that:\n"
                "1. Prints 'Hello, World!'\n"
                "2. Declares variables of 5 different data types and prints each\n"
                "3. Writes a function that takes two numbers and returns their sum\n"
                "Submit a .py file or a GitHub Gist link."
            ),
            "subject": "Introduction to Programming",
            "staff": "staff.alice",
            "status": AssignmentStatus.published,
            "due_date": datetime.utcnow() + timedelta(days=7),
            "max_score": 100.0,
            "ai_grading_enabled": True,
        },
        {
            "title": "Assignment 2: OOP & Classes",
            "description": (
                "Design a class hierarchy for a simple School system:\n"
                "- Base class: Person (name, age)\n"
                "- Subclasses: Student, Teacher\n"
                "- Implement __str__, __repr__, and at least 2 methods per class.\n"
                "Include docstrings and a main() demo."
            ),
            "subject": "Introduction to Programming",
            "staff": "staff.alice",
            "status": AssignmentStatus.published,
            "due_date": datetime.utcnow() + timedelta(days=21),
            "max_score": 100.0,
            "ai_grading_enabled": True,
        },
        {
            "title": "Linked List Implementation",
            "description": (
                "Implement a singly linked list in Python with:\n"
                "- insert(value): O(1) head insert\n"
                "- delete(value): remove first matching node\n"
                "- search(value): return node or None\n"
                "- display(): print all values\n"
                "Include Big-O analysis for each method."
            ),
            "subject": "Data Structures & Algorithms",
            "staff": "staff.alice",
            "status": AssignmentStatus.published,
            "due_date": datetime.utcnow() + timedelta(days=14),
            "max_score": 100.0,
            "ai_grading_enabled": True,
        },
        {
            "title": "SQL Schema Design Exercise",
            "description": (
                "Design a normalised relational schema for a Hospital system:\n"
                "- Entities: Patient, Doctor, Ward, Appointment\n"
                "- At minimum 3NF\n"
                "- Submit CREATE TABLE SQL statements with constraints and indexes.\n"
                "Justify each design choice in 2-3 sentences."
            ),
            "subject": "Database Systems",
            "staff": "staff.david",
            "status": AssignmentStatus.published,
            "due_date": datetime.utcnow() + timedelta(days=10),
            "max_score": 100.0,
            "ai_grading_enabled": True,
        },
        {
            "title": "Essay: Impact of AI in Education",
            "description": (
                "Write a 1500-word academic essay on the positive and negative "
                "impacts of Artificial Intelligence in modern education.\n"
                "Requirements: APA 7th edition references, min 5 scholarly sources, "
                "introduction-body-conclusion structure."
            ),
            "subject": "Academic Writing",
            "staff": "staff.carol",
            "status": AssignmentStatus.published,
            "due_date": datetime.utcnow() + timedelta(days=28),
            "max_score": 100.0,
            "ai_grading_enabled": True,
        },
    ]

    created: list[Assignment] = []
    for ad in assignment_definitions:
        subj = subjects.get(ad["subject"])
        if not subj:
            fail(f"Subject not found: {ad['subject']}")
            continue
        staff = staff_profiles.get(ad["staff"])
        if not staff:
            fail(f"Staff not found: {ad['staff']}")
            continue

        result = await session.execute(
            select(Assignment).where(
                Assignment.title == ad["title"],
                Assignment.subject_id == subj.id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            info(f"Assignment exists: {ad['title']}")
            created.append(existing)
            continue

        assignment = Assignment(
            id=uuid.uuid4(),
            title=ad["title"],
            description=ad["description"],
            subject_id=subj.id,
            staff_id=staff.id,
            status=ad["status"].value,
            due_date=ad["due_date"],
            max_score=ad["max_score"],
            ai_grading_enabled=ad["ai_grading_enabled"],
        )
        session.add(assignment)
        await session.flush()
        created.append(assignment)
        ok(f"Created assignment: {ad['title']}")

    return created


async def seed_attendance_sessions(
    session: AsyncSession,
    academic: dict,
    subjects: dict[str, Subject],
    staff_profiles: dict[str, StaffProfile],
    students: list[StudentProfile],
) -> None:
    head("Phase 8 — Sample Attendance Sessions")

    from app.models.attendance import AttendanceRecord, AttendanceStatus

    sessions_to_create = [
        {
            "subject": "Introduction to Programming",
            "staff": "staff.alice",
            "classroom_key": "cs_yr1",
            "date": date.today() - timedelta(days=1),
        },
        {
            "subject": "Introduction to Programming",
            "staff": "staff.alice",
            "classroom_key": "cs_yr1",
            "date": date.today() - timedelta(days=3),
        },
        {
            "subject": "Calculus I",
            "staff": "staff.bob",
            "classroom_key": "math_yr1",
            "date": date.today() - timedelta(days=2),
        },
    ]

    classrooms = academic["classrooms"]

    for att_def in sessions_to_create:
        subj = subjects.get(att_def["subject"])
        staff = staff_profiles.get(att_def["staff"])
        classroom = classrooms.get(att_def["classroom_key"])

        if not subj or not staff or not classroom:
            fail(f"Skipping attendance: missing subject/staff/classroom")
            continue

        result = await session.execute(
            select(AttendanceSession).where(
                AttendanceSession.subject_id == subj.id,
                AttendanceSession.date == att_def["date"],
            )
        )
        if result.scalar_one_or_none():
            info(f"Attendance session exists: {att_def['subject']} {att_def['date']}")
            continue

        att_session = AttendanceSession(
            id=uuid.uuid4(),
            classroom_id=classroom.id,
            subject_id=subj.id,
            staff_id=staff.id,
            date=att_def["date"],
        )
        session.add(att_session)
        await session.flush()

        # Only mark students in this classroom
        class_students = [
            s for s in students
            if s.classroom_id == classroom.id
        ]
        statuses = [
            AttendanceStatus.present, AttendanceStatus.present,
            AttendanceStatus.present, AttendanceStatus.late,
        ]
        for idx, stu in enumerate(class_students):
            status = statuses[idx % len(statuses)]
            record = AttendanceRecord(
                id=uuid.uuid4(),
                session_id=att_session.id,
                student_id=stu.id,
                status=status.value,
                remarks="Auto-seeded" if status != AttendanceStatus.present else None,
            )
            session.add(record)

        await session.flush()
        ok(f"Created attendance: {att_def['subject']} on {att_def['date']} "
           f"({len(class_students)} students)")


# ── main orchestrator ─────────────────────────────────────────────────────────

async def run_seed(admin_only: bool = False) -> None:
    print(f"\n{BOLD}{'='*60}")
    print(" LMS Production Seed Script")
    print(f"{'='*60}{RESET}")

    async with async_session_maker() as session:
        async with session.begin():
            # 1. Admin
            await seed_admin(session)

            if admin_only:
                print(f"\n{GREEN}{BOLD}Admin-only seed complete.{RESET}")
                return

            # 2. Academic structure
            academic = await seed_academic_structure(session)

            # 3. Staff
            staff_profiles = await seed_staff(session, academic)

            # 4. Subjects
            subjects = await seed_subjects(session, academic, staff_profiles)

            # 5. Students
            students = await seed_students(session, academic)

            # 6. Quizzes
            await seed_quizzes(session, subjects, staff_profiles)

            # 7. Assignments
            await seed_assignments(session, subjects, staff_profiles)

            # 8. Attendance
            await seed_attendance_sessions(
                session, academic, subjects, staff_profiles, students
            )

    head("Seed Complete")
    print(f"\n{GREEN}{BOLD}Production database seeded successfully!{RESET}")
    print(f"\n{CYAN}Default credentials:{RESET}")
    print("  Admin:    admin / AdminPass123!")
    print("  Staff:    staff.alice / StaffPass123!")
    print("  Student:  stu.emma / StudPass123!")
    print(f"\n{YELLOW}⚠  Change all passwords immediately after first login.{RESET}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the LMS production database with demo data."
    )
    parser.add_argument(
        "--admin-only",
        action="store_true",
        help="Only create the super-admin user and exit",
    )
    args = parser.parse_args()

    asyncio.run(run_seed(admin_only=args.admin_only))


if __name__ == "__main__":
    main()
