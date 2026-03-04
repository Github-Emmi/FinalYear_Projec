"""
SERVICE LAYER ARCHITECTURE & REFERENCE GUIDE
==============================================

Complete guide to the Service Layer implementation for business logic
and orchestration in the School Management System (LMS).

This document covers:
1. Architecture Overview
2. BaseService Foundation
3. AuthService Deep Dive
4. Integration with FastAPI Endpoints
5. Error Handling Patterns
6. Testing Strategies
7. Best Practices


═══════════════════════════════════════════════════════════════════════════════
1. ARCHITECTURE OVERVIEW
═══════════════════════════════════════════════════════════════════════════════

Service Layer Responsibilities:
- Business logic orchestration
- Data validation and consistency
- Transaction management (ACID properties)
- Authorization and permission checks
- Logging and audit trails
- Error handling and recovery

Service Layer Architecture:

    ┌─────────────────────────────────────┐
    │   FastAPI Endpoint / Route          │
    │   - Request validation              │
    │   - Response formatting             │
    │   - HTTP status codes               │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │   Service Layer                     │
    │   - Business logic                  │
    │   - Transaction coordination        │
    │   - Complex workflows               │
    │   - Authorization checks            │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │   Repository Layer                  │
    │   - Data access                     │
    │   - SQL abstraction                 │
    │   - Query optimization              │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │   Database                          │
    │   - Persistent storage              │
    │   - ACID transactions               │
    └─────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
2. BASESERVICE FOUNDATION
═══════════════════════════════════════════════════════════════════════════════

BaseService[T] is the foundation for all domain services.

When to Use BaseService:
✓ You need repository access for data operations
✓ You need structured logging for audit trails
✓ You need transaction management
✓ You need common validation utilities
✓ You need error handling consistently

BaseService Provides:

A. Dependency Injection
────────────────────
    class AuthService(BaseService[CustomUser]):
        def __init__(self, repos: RepositoryFactory) -> None:
            super().__init__(repos)
            # Now available:
            # self.repos - Full repository factory
            # self.logger - Configured logger
            # self.verify_user_exists()
            # self.transaction() context manager

B. Transaction Management
────────────────────────
    async with self.transaction():
        # Multiple repository operations
        user = await self.repos.user.create(user_data)
        await self.repos.student.create(student_data)
        # Commits on success, rolls back on error
        
    await self.commit()    # Manual commit
    await self.rollback()  # Manual rollback
    await self.flush()     # Flush without commit

C. Validation Utilities
──────────────────────
    # Email validation
    self._validate_email_format("user@school.edu")
    
    # Password strength validation
    self._validate_password_strength("SecurePass123!")
    
    # Field length validation
    self._validate_field_length(username, "username", min_len=3, max_len=20)
    
    # Enum choice validation
    self._validate_enum_choice(role, "role", ["ADMIN", "STAFF", "STUDENT"])
    
    # Required field validation
    self._validate_required_field(email, "email", value_type=str)

D. Logging & Audit
──────────────────
    # Structured audit logging
    self.log_audit(
        action="LOGIN",
        entity="User",
        entity_id=user.id,
        user_id=current_user.id,
        status="SUCCESS"
    )
    
    # Regular logging
    self.logger.info(f"User {user.id} created")
    self.logger.warning(f"Invalid login attempt from {ip}")
    self.logger.error(f"Database error: {str(e)}")

E. Response Formatting
──────────────────────
    # Success response
    return self.success_response(
        message="User created",
        data=user,
        access_token=token
    )
    # Returns: {
    #     "success": True,
    #     "message": "User created",
    #     "data": {...},
    #     "access_token": "..."
    # }
    
    # Error response
    return self.error_response(
        message="Validation failed",
        error_code="INVALID_EMAIL",
        details={"email": "Invalid format"}
    )
    # Returns: {
    #     "success": False,
    #     "message": "Validation failed",
    #     "error_code": "INVALID_EMAIL",
    #     "details": {...}
    # }

F. Access Control Utilities
───────────────────────────
    # Verify user exists
    await self.verify_user_exists(user_id)
    
    # Verify owner access (for self-service operations)
    await self.verify_owner_access(
        resource_owner_id=student.user_id,
        user_id=current_user.id,
        resource_name="student profile"
    )
    
    # Verify admin-only operation
    await self.verify_admin_access(current_user.role)
    
    # Verify staff or admin
    await self.verify_staff_or_admin_access(current_user.role)


═══════════════════════════════════════════════════════════════════════════════
3. AUTHSERVICE DEEP DIVE
═══════════════════════════════════════════════════════════════════════════════

AuthService handles user authentication lifecycle.

Methods:

A. register_user()
──────────────────
    async def register_user(
        email: str,
        username: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str = "STUDENT"
    ) -> dict

Purpose:
    Register new user with validation and password hashing

Process:
    1. Validate email format
    2. Validate username length (3-20 chars)
    3. Validate password strength
    4. Check email uniqueness
    5. Check username uniqueness
    6. Hash password with BCrypt
    7. Create user in database
    8. Generate JWT tokens (access + refresh)
    9. Log audit trail
    10. Return user data with tokens

Returns:
    {
        "success": True,
        "message": "User registered successfully",
        "data": {
            "id": "uuid",
            "email": "user@school.edu",
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "role": "STUDENT",
            ...
        },
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer",
        "expires_in": 900
    }

Errors:
    - ValidationError: If format/validation fails
    - ConflictError: If email or username exists

Example:
    result = await auth_service.register_user(
        email="john@school.edu",
        username="john_doe",
        password="SecurePass123!",
        first_name="John",
        last_name="Doe",
        role="STUDENT"
    )
    if result["success"]:
        token = result["access_token"]


B. login_user()
───────────────
    async def login_user(email: str, password: str) -> dict

Purpose:
    Authenticate user and generate JWT tokens

Process:
    1. Validate email format
    2. Find user by email (case-insensitive)
    3. Verify password hash
    4. Check user is active
    5. Generate access token (15 min expiry)
    6. Generate refresh token (7 day expiry)
    7. Update last_login timestamp
    8. Log audit trail
    9. Return tokens and user

Returns:
    {
        "success": True,
        "message": "Login successful",
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer",
        "expires_in": 900,
        "user": {
            "id": "uuid",
            "email": "john@school.edu",
            "username": "john_doe",
            "role": "STUDENT",
            ...
        }
    }

Errors:
    - UnauthorizedError: If email not found or password invalid
    - UnauthorizedError: If user is inactive

Example:
    result = await auth_service.login_user(
        email="john@school.edu",
        password="SecurePass123!"
    )
    if result["success"]:
        user = result["user"]
        token = result["access_token"]


C. refresh_access_token()
──────────────────────────
    async def refresh_access_token(refresh_token: str) -> dict

Purpose:
    Generate new access token using valid refresh token

Process:
    1. Decode and validate refresh token
    2. Extract user ID from token payload
    3. Fetch user from database
    4. Verify user is active
    5. Generate new access token (15 min)
    6. Keep refresh token unchanged
    7. Return new tokens

Returns:
    {
        "success": True,
        "message": "Token refreshed successfully",
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer",
        "expires_in": 900
    }

Errors:
    - UnauthorizedError: If token invalid or expired
    - UnauthorizedError: If user not found or inactive

Example:
    result = await auth_service.refresh_access_token(refresh_token)
    if result["success"]:
        new_token = result["access_token"]


D. validate_token()
────────────────────
    async def validate_token(token: str) -> CustomUser

Purpose:
    Validate JWT token and return authenticated user

Process:
    1. Decode JWT token
    2. Validate signature
    3. Check expiry
    4. Extract user ID
    5. Fetch user from database
    6. Return user object

Returns:
    CustomUser object

Errors:
    - UnauthorizedError: If token invalid or expired
    - UnauthorizedError: If user not found

Usage (in dependency):
    async def get_current_user(
        token: str = Header(...),
        services: ServiceFactory = Depends(get_services)
    ) -> CustomUser:
        return await services.auth.validate_token(token)


E. logout_user()
─────────────────
    async def logout_user(user_id: UUID) -> dict

Purpose:
    Logout user and clear sessions

Returns:
    {
        "success": True,
        "message": "Logged out successfully"
    }

Errors:
    - NotFoundError: If user doesn't exist


F. change_password()
─────────────────────
    async def change_password(
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> dict

Purpose:
    Change user password with verification

Process:
    1. Fetch user
    2. Verify current password
    3. Validate new password strength
    4. Prevent reuse of same password
    5. Hash new password
    6. Update in database
    7. Log audit trail

Returns:
    {
        "success": True,
        "message": "Password changed successfully"
    }

Errors:
    - UnauthorizedError: If current password invalid
    - ValidationError: If new password invalid


G. request_password_reset()
────────────────────────────
    async def request_password_reset(email: str) -> dict

Purpose:
    Initiate password reset for user

Process:
    1. Validate email format
    2. Find user by email
    3. Generate reset token
    4. Send reset email
    5. Return success (doesn't reveal if email exists - security)

Returns:
    {
        "success": True,
        "message": "If email exists, password reset link will be sent"
    }


═══════════════════════════════════════════════════════════════════════════════
4. INTEGRATION WITH FASTAPI ENDPOINTS
═══════════════════════════════════════════════════════════════════════════════

Services are injected into endpoints via dependency injection.

Basic Pattern:

    from fastapi import APIRouter, Depends, HTTPException, status
    from app.services import ServiceFactory, get_services
    from app.schemas.auth import UserLogin, UserRegister, TokenResponse
    
    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
    
    @router.post("/register", response_model=TokenResponse)
    async def register(
        request: UserRegister,
        services: ServiceFactory = Depends(get_services)
    ):
        try:
            result = await services.auth.register_user(
                email=request.email,
                username=request.username,
                password=request.password,
                first_name=request.first_name,
                last_name=request.last_name,
                role="STUDENT"
            )
            if result["success"]:
                return result
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.post("/login", response_model=TokenResponse)
    async def login(
        request: UserLogin,
        services: ServiceFactory = Depends(get_services)
    ):
        try:
            result = await services.auth.login_user(
                email=request.email,
                password=request.password
            )
            if result["success"]:
                return result
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=result["message"]
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @router.post("/refresh", response_model=TokenResponse)
    async def refresh_token(
        request: RefreshTokenRequest,
        services: ServiceFactory = Depends(get_services)
    ):
        result = await services.auth.refresh_access_token(
            refresh_token=request.refresh_token
        )
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=401, detail=result["message"])


Dependency for Current User:

    from fastapi import Header
    from app.models.user import CustomUser
    
    async def get_current_user(
        token: str = Header(..., alias="authorization"),
        services: ServiceFactory = Depends(get_services)
    ) -> CustomUser:
        try:
            # Remove "Bearer " prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            return await services.auth.validate_token(token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    
    @router.get("/me")
    async def get_current_user_profile(
        current_user: CustomUser = Depends(get_current_user)
    ):
        return UserResponse.model_validate(current_user)


═══════════════════════════════════════════════════════════════════════════════
5. ERROR HANDLING PATTERNS
═══════════════════════════════════════════════════════════════════════════════

Services raise custom exceptions that endpoints handle.

Exception Hierarchy:

    from app.core.exceptions import (
        ValidationError,      # Invalid input
        UnauthorizedError,    # Auth failed
        NotFoundError,        # Resource not found
        ForbiddenError,       # Access denied
        ConflictError,        # Resource exists
        InternalServerError,  # Server error
    )

Pattern in Service:

    async def register_user(...) -> dict:
        # Input validation
        self._validate_email_format(email)
        if not email:
            raise ValidationError("Email required")
        
        # Check uniqueness
        if await self.repos.user.email_exists(email):
            raise ConflictError("Email already registered")
        
        # Database operation
        try:
            user = await self.repos.user.create(user_data)
            await self.commit()
            self.log_audit(action="REGISTER", entity="User", entity_id=user.id)
            return self.success_response(data=user)
        except Exception as e:
            await self.rollback()
            self.logger.error(f"Registration error: {str(e)}")
            raise InternalServerError("Registration failed")

Pattern in Endpoint:

    @router.post("/register")
    async def register(request: UserRegister, services = Depends(get_services)):
        try:
            result = await services.auth.register_user(...)
            return result
        
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except ConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        except UnauthorizedError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred"
            )


═══════════════════════════════════════════════════════════════════════════════
6. TESTING STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

Unit Testing Services (Mock repositories):

    import pytest
    from unittest.mock import AsyncMock, MagicMock
    from app.services import AuthService
    from app.repositories.factory import RepositoryFactory
    
    @pytest.fixture
    def mock_repos():
        repos = MagicMock(spec=RepositoryFactory)
        repos.user = AsyncMock()
        repos.commit = AsyncMock()
        repos.rollback = AsyncMock()
        return repos
    
    @pytest.mark.asyncio
    async def test_register_user_success(mock_repos):
        # Arrange
        auth_service = AuthService(mock_repos)
        mock_repos.user.email_exists.return_value = False
        mock_repos.user.username_exists.return_value = False
        mock_repos.user.create.return_value = MagicMock(id="uuid-123")
        
        # Act
        result = await auth_service.register_user(
            email="test@school.edu",
            username="testuser",
            password="SecurePass123!",
            first_name="Test",
            last_name="User"
        )
        
        # Assert
        assert result["success"] is True
        assert result["access_token"] is not None
        assert result["refresh_token"] is not None
    
    @pytest.mark.asyncio
    async def test_register_user_email_exists(mock_repos):
        # Arrange
        auth_service = AuthService(mock_repos)
        mock_repos.user.email_exists.return_value = True
        
        # Act & Assert
        with pytest.raises(ConflictError):
            await auth_service.register_user(
                email="existing@school.edu",
                username="newuser",
                password="SecurePass123!",
                first_name="Test",
                last_name="User"
            )


Integration Testing (Real database):

    @pytest.mark.asyncio
    async def test_register_and_login_flow(async_session):
        # Arrange
        repos = RepositoryFactory(async_session)
        auth_service = AuthService(repos)
        
        # Act - Register
        register_result = await auth_service.register_user(
            email="integration@test.edu",
            username="integuser",
            password="IntegPass123!",
            first_name="Integration",
            last_name="Test"
        )
        
        # Assert - Registration
        assert register_result["success"] is True
        
        # Act - Login
        login_result = await auth_service.login_user(
            email="integration@test.edu",
            password="IntegPass123!"
        )
        
        # Assert - Login
        assert login_result["success"] is True
        assert login_result["access_token"] is not None


═══════════════════════════════════════════════════════════════════════════════
7. BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════

✓ DO:

1. Always use BaseService as parent class
   class UserService(BaseService[CustomUser]):
       ...

2. Use repositories for ALL data access
   user = await self.repos.user.get_by_id(user_id)
   # NOT: await self.db_session.execute(select(...))

3. Validate inputs at service level
   self._validate_email_format(email)
   self._validate_password_strength(password)

4. Use transaction() context manager for multi-step operations
   async with self.transaction():
       await self.repos.user.create(user_data)
       await self.repos.student.create(student_data)

5. Log business operations
   self.log_audit(action="LOGIN", entity="User", entity_id=user.id)

6. Handle errors explicitly
   try:
       ...
   except ConflictError:
       raise  # Re-raise known errors
   except Exception as e:
       self.logger.error(...)
       raise InternalServerError(...)

7. Return consistent response format
   return self.success_response(data=user, message="Created")
   return self.error_response(message="Failed", error_code="CODE")

8. Keep functions under 40 lines (Single Responsibility)

9. Use type hints on all methods
   async def my_method(self, param: str) -> dict:

10. Check authorization before operations
    await self.verify_admin_access(user.role)
    await self.verify_owner_access(owner_id, user_id)

✗ DON'T:

1. Don't import AsyncSession directly - use repos
2. Don't execute raw SQL queries - use repositories
3. Don't log sensitive data (passwords, tokens, SSN)
4. Don't swallow exceptions - always log and re-raise
5. Don't mix HTTP logic with business logic
6. Don't create multiple RepositoryFactory instances
7. Don't forget to commit() - changes stay pending
8. Don't validate only at endpoint level - validate in service
9. Don't assume user is logged in - always verify token
10. Don't hardcode business rules - parameterize them


═══════════════════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════════════════

Service Layer provides:
✓ Business logic encapsulation
✓ Transaction management (ACID)
✓ Consistent error handling
✓ Audit logging
✓ Type-safe operations
✓ Validation orchestration
✓ DRY principles (no duplication)

Key Components:
1. BaseService[T] - Foundation with common utilities
2. AuthService - User authentication and token management
3. ServiceFactory - Dependency injection and lazy loading
4. get_services() - FastAPI dependency function

Usage Pattern:
    @app.post("/endpoint")
    async def endpoint(
        data: RequestSchema,
        services: ServiceFactory = Depends(get_services)
    ):
        result = await services.auth.some_method(...)
        if result["success"]:
            return result
        raise HTTPException(status_code=400, detail=result["message"])

Next Steps:
→ Create remaining services (User, Student, Quiz, etc.)
→ Create API endpoints with dependency injection
→ Write comprehensive tests
→ Deploy to production with monitoring
"""
