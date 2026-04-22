"""Analytics endpoints: per-student, per-classroom, per-staff summaries."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import StaffOrAdmin
from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/students/{student_id}", dependencies=[Depends(StaffOrAdmin)])
async def student_analytics(student_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    return await svc.student_summary(student_id)


@router.get("/classrooms/{classroom_id}", dependencies=[Depends(StaffOrAdmin)])
async def classroom_analytics(classroom_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    return await svc.classroom_summary(classroom_id)


@router.get("/staff/{staff_id}", dependencies=[Depends(StaffOrAdmin)])
async def staff_analytics(staff_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AnalyticsService(db)
    return await svc.staff_summary(staff_id)
