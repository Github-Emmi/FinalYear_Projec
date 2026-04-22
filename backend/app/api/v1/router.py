"""API v1 router — aggregates all domain sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints.academic import router as academic_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.assessments import router as assessments_router
from app.api.v1.endpoints.assignments import router as assignments_router
from app.api.v1.endpoints.attendance import router as attendance_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.leave import router as leave_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.staff import router as staff_router
from app.api.v1.endpoints.students import router as students_router
from app.api.v1.endpoints.users import router as users_router

router = APIRouter()


# Health check — retained from Phase 1 (used by Docker healthcheck)
@router.get("/health", tags=["health"])
async def health_check():
    """Returns 200 OK. Used by Docker healthchecks and load balancers."""
    return {"status": "ok", "version": "1.0.0"}


# Domain routers
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(students_router)
router.include_router(staff_router)
router.include_router(academic_router)
router.include_router(assessments_router)
router.include_router(assignments_router)
router.include_router(attendance_router)
router.include_router(leave_router)
router.include_router(notifications_router)
router.include_router(analytics_router)
