"""
REPOSITORY PATTERN REFERENCE GUIDE
==================================

Complete guide to the Repository Pattern implementation in this FastAPI backend.
This document covers architecture, usage patterns, and best practices.

TABLE OF CONTENTS
-----------------
1. Architecture Overview
2. Repository Layer Structure
3. Using Repositories in Endpoints
4. Example Queries
5. Transaction Management
6. Best Practices
7. Common Patterns


═══════════════════════════════════════════════════════════════════════════════
1. ARCHITECTURE OVERVIEW
═══════════════════════════════════════════════════════════════════════════════

The Repository Pattern provides:
✓ Abstraction over database operations
✓ Type-safe queries using SQLAlchemy async
✓ Business logic encapsulation
✓ Clean separation of concerns
✓ Easy testing and mocking
✓ Consistent CRUD interface across entities

Structure:

    ┌─────────────────────────────────────────────────────┐
    │           FastAPI Endpoints / Routes               │
    └────────────────────┬────────────────────────────────┘
                         │
                         ▼
    ┌─────────────────────────────────────────────────────┐
    │    Service Layer (Business Logic)                  │
    │    - Validation                                    │
    │    - Orchestration                                 │
    │    - Transaction management                        │
    └────────────────────┬────────────────────────────────┘
                         │
                         ▼
    ┌─────────────────────────────────────────────────────┐
    │    Repository Factory (Dependency Injection)       │
    │    - Provides access to all repositories           │
    │    - Manages database sessions                     │
    │    - Controls transactions                         │
    └────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
    ┌──────────────────┐          ┌──────────────────┐
    │ UserRepository   │          │ StudentRepository│
    │ StaffRepository  │          │ QuizRepository   │
    │ ... etc          │          │ ... etc          │
    │                  │          │                  │
    │ (All inherit     │          │ (All inherit     │
    │  from            │          │  from            │
    │  BaseRepository) │          │  BaseRepository) │
    └────────┬─────────┘          └────────┬─────────┘
             │                             │
             └─────────────┬───────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │    BaseRepository[T]                 │
        │    - Generic CRUD operations         │
        │    - Transaction control             │
        └──────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │    SQLAlchemy AsyncSession           │
        │    (Database connection)             │
        └──────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
2. REPOSITORY LAYER STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

Directory Structure:
    app/repositories/
    ├── __init__.py                 # Module exports & dependency injection
    ├── base.py                     # BaseRepository generic CRUD
    ├── user.py                     # UserRepository (authentication)
    ├── student.py                  # StudentRepository (enrollment)
    ├── staff.py                    # StaffRepository & AdminHODRepository
    ├── academic.py                 # 5 academic structure repositories
    ├── quiz.py                     # QuizRepository (assessments)
    ├── assignment.py               # AssignmentRepository (submissions)
    ├── attendance.py               # AttendanceRepository (tracking)
    ├── leave.py                    # StudentLeaveRepository & StaffLeaveRepository
    ├── feedback.py                 # Feedback, Message, AnnouncementRepository
    ├── notification.py             # Notification, Preferences, ReminderRepository
    └── factory.py                  # RepositoryFactory (DI & lazy loading)


BASE REPOSITORY - BaseRepository[T]
──────────────────────────────────

Generic CRUD operations (13 methods):

    CREATE OPERATIONS:
    - create(data_dict) → object
        Create single record from dictionary
        
    - create_bulk(data_list) → List[object]
        Create multiple records efficiently
    
    READ OPERATIONS:
    - get_by_id(id) → object | None
        Fetch by primary key
        
    - list(skip=0, limit=10) → (List[object], total_count)
        Paginated list with total count
        
    - get_all() → List[object]
        Fetch all records without pagination
        
    - first() → object | None
        Get first record (useful for defaults)
        
    - count() → int
        Get total count
    
    UPDATE OPERATIONS:
    - update(obj, update_dict) → object
        Update existing object
        
    - update_by_id(id, update_dict) → object | None
        Update by ID
    
    DELETE OPERATIONS:
    - delete(id) → bool
        Soft delete (sets is_deleted=True)
        
    - hard_delete(id) → bool
        Permanent delete from database
        
    - delete_bulk(id_list) → int
        Delete multiple records, returns count
    
    UTILITY:
    - exists(id) → bool
        Check if record exists


TRANSACTION CONTROL - In BaseRepository & RepositoryFactory
──────────────────────────────────────────────────────────

    flush() → None
        Flush pending changes to database (no commit)
        Use: Before checking new IDs, before nested operations
        
    commit() → None
        Commit transaction to database
        Use: After completing all operations in unit of work
        
    rollback() → None
        Rollback all pending changes
        Use: On error or when operations fail validation


═══════════════════════════════════════════════════════════════════════════════
3. USING REPOSITORIES IN ENDPOINTS
═══════════════════════════════════════════════════════════════════════════════

Dependency Injection Pattern:

    from fastapi import APIRouter, Depends, HTTPException
    from app.repositories import get_repos, RepositoryFactory
    
    router = APIRouter()
    
    @router.get("/students")
    async def list_students(
        skip: int = 0,
        limit: int = 10,
        repos: RepositoryFactory = Depends(get_repos)  # ← DI here
    ):
        # Access repositories through factory
        students, total = await repos.student.list(skip=skip, limit=limit)
        return {
            "data": students,
            "total": total,
            "skip": skip,
            "limit": limit
        }


Simple CRUD Example:

    @router.post("/students")
    async def create_student(
        student_data: StudentCreateSchema,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        # Create
        student = await repos.student.create(student_data.dict())
        await repos.commit()  # Commit transaction
        return student
    
    @router.get("/students/{student_id}")
    async def get_student(
        student_id: UUID,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        # Read
        student = await repos.student.get_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404)
        return student
    
    @router.put("/students/{student_id}")
    async def update_student(
        student_id: UUID,
        update_data: StudentUpdateSchema,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        # Update
        student = await repos.student.get_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404)
        
        updated = await repos.student.update(student, update_data.dict())
        await repos.commit()
        return updated
    
    @router.delete("/students/{student_id}")
    async def delete_student(
        student_id: UUID,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        # Delete (soft delete)
        success = await repos.student.delete(student_id)
        if success:
            await repos.commit()
            return {"message": "Student deleted"}
        raise HTTPException(status_code=404)


Multi-Repository Transaction Example:

    @router.post("/students/{student_id}/enroll")
    async def enroll_student(
        student_id: UUID,
        class_id: UUID,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        try:
            # Multiple operations
            student = await repos.student.get_by_id(student_id)
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            
            class_obj = await repos.class_repo.get_by_id(class_id)
            if not class_obj:
                raise HTTPException(status_code=404, detail="Class not found")
            
            # Complex operation
            student.current_class_id = class_id
            await repos.student.update(student, {"current_class_id": class_id})
            
            # Create enrollment record
            enrollment = await repos.student.create_enrollment({
                "student_id": student_id,
                "class_id": class_id
            })
            
            # All-or-nothing: commit or rollback
            await repos.commit()
            return enrollment
            
        except Exception as e:
            await repos.rollback()
            raise HTTPException(status_code=400, detail=str(e))


═══════════════════════════════════════════════════════════════════════════════
4. EXAMPLE QUERIES
═══════════════════════════════════════════════════════════════════════════════

USER REPOSITORY
───────────────

    # Authentication
    user = await repos.user.get_by_email("student@school.edu")
    user = await repos.user.get_by_username("john_doe")
    
    # Availability checks
    exists = await repos.user.email_exists("test@school.edu")
    exists = await repos.user.username_exists("john_doe")
    
    # Role-based queries
    admins = await repos.user.get_by_role("ADMIN")
    staff = await repos.user.get_by_role("STAFF")
    students = await repos.user.get_by_role("STUDENT")
    
    # Status queries
    active_users = await repos.user.get_active_users()
    inactive = await repos.user.get_inactive_users()
    
    # Search
    results, total = await repos.user.search_by_name("John", skip=0, limit=20)
    
    # Activity tracking
    await repos.user.mark_verified(user_id)
    await repos.user.update_last_login(user_id)
    await repos.user.deactivate_user(user_id)


STUDENT REPOSITORY
──────────────────

    # Class-based queries
    students = await repos.student.get_by_class(class_id, session_year_id)
    students = await repos.student.get_by_department(dept_id, session_id)
    
    # Search
    results, total = await repos.student.search("John", skip=0, limit=10)
    
    # Performance ranking
    top_students = await repos.student.get_high_performers(class_id, min_gpa=3.5)
    at_risk = await repos.student.get_low_performers(class_id, max_gpa=2.0)
    
    # Status filtering
    active = await repos.student.get_active_students()
    withdrawn = await repos.student.get_withdrawn_students()
    graduated = await repos.student.get_graduated_students()
    
    # Statistics
    count = await repos.student.count_by_class(class_id)
    count = await repos.student.count_by_status(session_id, "ACTIVE")


QUIZ REPOSITORY
───────────────

    # Status filtering
    published = await repos.quiz.get_published_quizzes(class_id)
    drafts = await repos.quiz.get_draft_quizzes(staff_id)
    
    # Timeline filtering
    active = await repos.quiz.get_active_quizzes(class_id)
    upcoming = await repos.quiz.get_upcoming_quizzes(class_id)
    past = await repos.quiz.get_past_quizzes(class_id)
    
    # With relationships
    quiz = await repos.quiz.get_quiz_with_questions(quiz_id)
    
    # Submissions
    submissions = await repos.quiz.get_student_submissions(quiz_id)
    submission = await repos.quiz.get_student_quiz_submission(quiz_id, student_id)
    
    # Statistics
    stats = await repos.quiz.get_quiz_statistics(quiz_id)
    # Returns: avg_score, max_score, min_score, pass_rate, total_attempts


ATTENDANCE REPOSITORY
─────────────────────

    # Student records
    records = await repos.attendance.get_student_attendance(student_id, session_id)
    records = await repos.attendance.get_student_attendance_by_date_range(
        student_id, start_date, end_date
    )
    
    # Class records
    records = await repos.attendance.get_class_attendance_on_date(class_id, date)
    records = await repos.attendance.get_class_attendance_by_date_range(
        class_id, start_date, end_date
    )
    
    # Status counts
    present = await repos.attendance.count_by_status(
        student_id, "PRESENT", session_id
    )
    
    # Calculations
    percentage = await repos.attendance.calculate_attendance_percentage(
        student_id, session_id
    )  # Returns 0-100 (PRESENT + LATE*0.75)
    
    # Reports
    stats = await repos.attendance.get_class_attendance_statistics(class_id, date)
    absentees = await repos.attendance.get_chronic_absentees()


ASSIGNMENT REPOSITORY
─────────────────────

    # Filtering
    assignments = await repos.assignment.get_class_assignments(class_id)
    assignments = await repos.assignment.get_subject_assignments(subject_id)
    
    # Timeline
    active = await repos.assignment.get_active_assignments(class_id)
    upcoming = await repos.assignment.get_upcoming_assignments(class_id)
    overdue = await repos.assignment.get_overdue_assignments()
    
    # Submissions
    submissions, total = await repos.assignment.get_submissions(
        assignment_id, skip=0, limit=50
    )
    submission = await repos.assignment.get_student_submission(
        assignment_id, student_id
    )
    
    # Grading
    ungraded = await repos.assignment.get_ungraded_submissions(assignment_id)
    late = await repos.assignment.get_late_submissions(assignment_id)
    
    # Statistics
    stats = await repos.assignment.get_assignment_statistics()


NOTIFICATION REPOSITORY
───────────────────────

    # User notifications
    notifications = await repos.notification.get_user_notifications(user_id)
    unread = await repos.notification.get_unread_notifications(user_id)
    
    # Filtering
    unread_count = await repos.notification.count_unread(user_id)
    by_type = await repos.notification.get_by_type(user_id, "QUIZ_AVAILABLE")
    by_priority = await repos.notification.get_by_priority(user_id, "HIGH")
    
    # Status management
    await repos.notification.mark_as_read(notification_id)
    await repos.notification.mark_all_as_read(user_id)


═══════════════════════════════════════════════════════════════════════════════
5. TRANSACTION MANAGEMENT
═══════════════════════════════════════════════════════════════════════════════

Simple Transaction:

    try:
        # All operations pending
        user = await repos.user.create({"email": "new@school.edu"})
        
        # Flush to get ID before next query
        await repos.flush()
        
        # Use the ID
        await repos.user.mark_verified(user.id)
        
        # Commit everything
        await repos.commit()
        return user
    except Exception as e:
        await repos.rollback()
        raise


Complex Multi-Repository Transaction:

    try:
        # Step 1: Create student
        student = await repos.student.create({
            "user_id": user_id,
            "admission_number": "ADM-2024-001"
        })
        await repos.flush()  # Get ID
        
        # Step 2: Enroll in class
        await repos.student.create_enrollment({
            "student_id": student.id,
            "class_id": class_id
        })
        
        # Step 3: Create notifications
        await repos.notification.create({
            "user_id": student.user_id,
            "title": "Welcome to school",
            "type": "WELCOME"
        })
        
        # All or nothing: commit everything
        await repos.commit()
        return student
        
    except Exception as e:
        await repos.rollback()
        raise HTTPException(status_code=400, detail=str(e))


Nested Transaction Prevention:
⚠️  Don't create nested transactions - Always use single RepositoryFactory


═══════════════════════════════════════════════════════════════════════════════
6. BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════

✓ DO:
  ✓ Use get_repos dependency injection in endpoints
  ✓ Commit after each unit of work completes successfully
  ✓ Rollback on errors within try/except blocks
  ✓ Use list(skip, limit) for pagination
  ✓ Filter at repository level, not in endpoints
  ✓ Use eager loading (get_with_relationships) for related objects
  ✓ Use count() before list() if you need total before processing
  ✓ Check exists() before operations on optional entities

✗ DON'T:
  ✗ Don't import repositories directly - use dependency injection
  ✗ Don't mix database operations from different RepositoryFactory instances
  ✗ Don't forget to commit() - changes remain pending
  ✗ Don't use hard_delete() unless you really need permanent deletion
  ✗ Don't perform pagination without limit parameter
  ✗ Don't load full objects when you only need IDs (use select(Model.id))
  ✗ Don't create multiple AsyncSession instances in same request
  ✗ Don't skip error handling for database operations


Query Performance:

1. Use list() with pagination:
   items, total = await repos.model.list(skip=n, limit=10)
   
2. Use exists() before get_by_id():
   if await repos.model.exists(id):
       item = await repos.model.get_by_id(id)
   
3. Use eager loading for relationships:
   quiz = await repos.quiz.get_quiz_with_questions(quiz_id)
   # vs
   quiz = await repos.quiz.get_by_id(quiz_id)
   # questions loaded separately (N+1 problem)
   
4. Count separately from list:
   total = await repos.model.count()
   items, _ = await repos.model.list(skip=0, limit=10)


═══════════════════════════════════════════════════════════════════════════════
7. COMMON PATTERNS
═══════════════════════════════════════════════════════════════════════════════

PATTERN 1: Create with User Link

    @router.post("/students/register")
    async def register_student(
        data: StudentRegisterSchema,
        current_user: CustomUser = Depends(get_current_user),
        repos: RepositoryFactory = Depends(get_repos)
    ):
        student = await repos.student.create({
            "user_id": current_user.id,
            "admission_number": data.admission_number,
            "enrollment_date": datetime.now()
        })
        await repos.commit()
        return student


PATTERN 2: Check Before Update

    @router.put("/students/{student_id}")
    async def update_student(
        student_id: UUID,
        updates: StudentUpdateSchema,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        student = await repos.student.get_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404)
        
        updated = await repos.student.update(student, updates.dict())
        await repos.commit()
        return updated


PATTERN 3: Soft Delete with Verification

    @router.delete("/students/{student_id}")
    async def withdraw_student(
        student_id: UUID,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        student = await repos.student.get_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404)
        
        # Soft delete (sets is_deleted=True)
        await repos.student.delete(student_id)
        await repos.commit()
        
        return {"message": "Student withdrawn"}


PATTERN 4: Search with Pagination

    @router.get("/students/search")
    async def search_students(
        q: str,
        skip: int = 0,
        limit: int = 20,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        results, total = await repos.student.search(q, skip, limit)
        return {
            "data": results,
            "total": total,
            "query": q
        }


PATTERN 5: Bulk Operations

    @router.post("/attendance/bulk-mark")
    async def bulk_mark_attendance(
        records: List[AttendanceRecord],
        repos: RepositoryFactory = Depends(get_repos)
    ):
        created = await repos.attendance.create_bulk([
            record.dict() for record in records
        ])
        await repos.commit()
        return created


PATTERN 6: Statistics Report

    @router.get("/quizzes/{quiz_id}/statistics")
    async def quiz_statistics(
        quiz_id: UUID,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        stats = await repos.quiz.get_quiz_statistics(quiz_id)
        return {
            "quiz_id": quiz_id,
            "average_score": stats.get("avg_score"),
            "highest_score": stats.get("max_score"),
            "lowest_score": stats.get("min_score"),
            "pass_rate": f"{stats.get('pass_rate', 0):.1f}%",
            "total_attempts": stats.get("total_attempts")
        }


PATTERN 7: Relationship Eager Loading

    @router.get("/quizzes/{quiz_id}")
    async def get_quiz_details(
        quiz_id: UUID,
        repos: RepositoryFactory = Depends(get_repos)
    ):
        # Loads quiz with all questions at once
        quiz = await repos.quiz.get_quiz_with_questions(quiz_id)
        
        if not quiz:
            raise HTTPException(status_code=404)
        
        return {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "question_count": len(quiz.questions),
            "questions": quiz.questions
        }


═══════════════════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════════════════

The Repository Pattern provides:
✓ Consistent interface across all data operations
✓ Type-safe database queries with SQLAlchemy
✓ Business logic encapsulation in repository methods
✓ Easy testing through dependency injection
✓ Clean separation of concerns
✓ Scalable architecture

Key Components:
1. BaseRepository[T] - Generic CRUD for any model
2. Specialized Repositories - Domain-specific queries
3. RepositoryFactory - Central dependency injection
4. get_repos() - FastAPI dependency function

Always use:
@app.get("/endpoint")
async def endpoint(repos: RepositoryFactory = Depends(get_repos)):
    ...

Next Steps:
→ Phase 1 Step 5: Service Layer (Business logic orchestration)
→ Phase 1 Steps 6-8: API Endpoints (Using services)
→ Phase 1 Step 9: Testing & Documentation
"""
