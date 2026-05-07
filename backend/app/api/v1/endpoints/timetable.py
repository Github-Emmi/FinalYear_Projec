"""Timetable endpoints — admin-only CRUD for class timetable entries."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AdminOnly
from app.core.database import get_db
from app.models.academic import TimetableEntry
from app.models.staff import StaffProfile
from app.schemas.timetable import (
    TimetableEntryCreate,
    TimetableEntryResponse,
    TimetableEntryUpdate,
)

router = APIRouter(prefix="/academic/timetable", tags=["timetable"])

_LOADS = [
    selectinload(TimetableEntry.classroom),
    selectinload(TimetableEntry.subject),
    selectinload(TimetableEntry.staff).selectinload(StaffProfile.user),
]


@router.get("", response_model=dict, dependencies=[Depends(AdminOnly)])
async def list_timetable(
    classroom_id: UUID | None = None,
    session_year_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    q = select(TimetableEntry).options(*_LOADS).where(
        TimetableEntry.is_deleted.is_(False)
    )
    if classroom_id:
        q = q.where(TimetableEntry.classroom_id == classroom_id)
    if session_year_id:
        q = q.where(TimetableEntry.session_year_id == session_year_id)
    q = q.order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)
    result = await db.execute(q)
    entries = result.scalars().all()
    items = [TimetableEntryResponse.model_validate(e).model_dump() for e in entries]
    return {"items": items, "total": len(items)}


@router.post(
    "",
    response_model=TimetableEntryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(AdminOnly)],
)
async def create_timetable_entry(
    body: TimetableEntryCreate, db: AsyncSession = Depends(get_db)
) -> TimetableEntryResponse:
    entry = TimetableEntry(**body.model_dump())
    db.add(entry)
    await db.commit()
    # Reload with relationships
    result = await db.execute(
        select(TimetableEntry).options(*_LOADS).where(TimetableEntry.id == entry.id)
    )
    entry = result.scalar_one()
    return TimetableEntryResponse.model_validate(entry)


@router.patch(
    "/{entry_id}",
    response_model=TimetableEntryResponse,
    dependencies=[Depends(AdminOnly)],
)
async def update_timetable_entry(
    entry_id: UUID,
    body: TimetableEntryUpdate,
    db: AsyncSession = Depends(get_db),
) -> TimetableEntryResponse:
    result = await db.execute(
        select(TimetableEntry).options(*_LOADS).where(
            TimetableEntry.id == entry_id,
            TimetableEntry.is_deleted.is_(False),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return TimetableEntryResponse.model_validate(entry)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(AdminOnly)],
)
async def delete_timetable_entry(
    entry_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(
        select(TimetableEntry).where(
            TimetableEntry.id == entry_id,
            TimetableEntry.is_deleted.is_(False),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    entry.is_deleted = True
    await db.commit()
    return {"ok": True}
