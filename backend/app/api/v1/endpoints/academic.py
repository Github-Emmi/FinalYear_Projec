"""Academic entity endpoints: departments, session years, classrooms, subjects."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyAuthenticatedUser
from app.core.database import get_db
from app.schemas.academic import (
    ClassRoomCreate,
    ClassRoomResponse,
    ClassRoomUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    SessionYearCreate,
    SessionYearResponse,
    SessionYearUpdate,
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)
from app.services.academic_service import AcademicService

router = APIRouter(prefix="/academic", tags=["academic"])


# ── Departments ────────────────────────────────────────────────────────────────

@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_department(body: DepartmentCreate, db: AsyncSession = Depends(get_db)) -> DepartmentResponse:
    svc = AcademicService(db)
    dept = await svc.create_department(body)
    return DepartmentResponse.model_validate(dept)


@router.get("/departments", response_model=list[DepartmentResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_departments(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[DepartmentResponse]:
    svc = AcademicService(db)
    items = await svc.list_departments(skip=skip, limit=limit)
    return [DepartmentResponse.model_validate(i) for i in items]


@router.get("/departments/{dept_id}", response_model=DepartmentResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_department(dept_id: UUID, db: AsyncSession = Depends(get_db)) -> DepartmentResponse:
    svc = AcademicService(db)
    return DepartmentResponse.model_validate(await svc.get_department(dept_id))


@router.patch("/departments/{dept_id}", response_model=DepartmentResponse, dependencies=[Depends(AdminOnly)])
async def update_department(dept_id: UUID, body: DepartmentUpdate, db: AsyncSession = Depends(get_db)) -> DepartmentResponse:
    svc = AcademicService(db)
    return DepartmentResponse.model_validate(await svc.update_department(dept_id, body))


@router.delete("/departments/{dept_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_department(dept_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_department(dept_id)


# ── Session Years ──────────────────────────────────────────────────────────────

@router.post("/session-years", response_model=SessionYearResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_session_year(body: SessionYearCreate, db: AsyncSession = Depends(get_db)) -> SessionYearResponse:
    svc = AcademicService(db)
    return SessionYearResponse.model_validate(await svc.create_session_year(body))


@router.get("/session-years", response_model=list[SessionYearResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_session_years(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[SessionYearResponse]:
    svc = AcademicService(db)
    items = await svc.list_session_years(skip=skip, limit=limit)
    return [SessionYearResponse.model_validate(i) for i in items]


@router.get("/session-years/{year_id}", response_model=SessionYearResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_session_year(year_id: UUID, db: AsyncSession = Depends(get_db)) -> SessionYearResponse:
    return SessionYearResponse.model_validate(await AcademicService(db).get_session_year(year_id))


@router.patch("/session-years/{year_id}", response_model=SessionYearResponse, dependencies=[Depends(AdminOnly)])
async def update_session_year(year_id: UUID, body: SessionYearUpdate, db: AsyncSession = Depends(get_db)) -> SessionYearResponse:
    return SessionYearResponse.model_validate(await AcademicService(db).update_session_year(year_id, body))


@router.delete("/session-years/{year_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_session_year(year_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_session_year(year_id)


# ── ClassRooms ─────────────────────────────────────────────────────────────────

@router.post("/classrooms", response_model=ClassRoomResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_classroom(body: ClassRoomCreate, db: AsyncSession = Depends(get_db)) -> ClassRoomResponse:
    return ClassRoomResponse.model_validate(await AcademicService(db).create_classroom(body))


@router.get("/classrooms", response_model=dict, dependencies=[Depends(AnyAuthenticatedUser)])
async def list_classrooms(page: int = 1, size: int = 100, skip: int = 0, limit: int = 0, db: AsyncSession = Depends(get_db)) -> dict:
    effective_skip = skip if skip else (page - 1) * size
    effective_limit = limit if limit else size
    items = await AcademicService(db).list_classrooms(skip=effective_skip, limit=effective_limit)
    validated = [ClassRoomResponse.model_validate(i) for i in items]
    return {"items": [v.model_dump() for v in validated], "total": len(validated), "page": max(page, 1), "size": effective_limit}


@router.get("/classrooms/{room_id}", response_model=ClassRoomResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_classroom(room_id: UUID, db: AsyncSession = Depends(get_db)) -> ClassRoomResponse:
    return ClassRoomResponse.model_validate(await AcademicService(db).get_classroom(room_id))


@router.patch("/classrooms/{room_id}", response_model=ClassRoomResponse, dependencies=[Depends(AdminOnly)])
async def update_classroom(room_id: UUID, body: ClassRoomUpdate, db: AsyncSession = Depends(get_db)) -> ClassRoomResponse:
    return ClassRoomResponse.model_validate(await AcademicService(db).update_classroom(room_id, body))


@router.delete("/classrooms/{room_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_classroom(room_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_classroom(room_id)


# ── Subjects ───────────────────────────────────────────────────────────────────

@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def create_subject(body: SubjectCreate, db: AsyncSession = Depends(get_db)) -> SubjectResponse:
    return SubjectResponse.from_orm_obj(await AcademicService(db).create_subject(body))


@router.get("/subjects", response_model=list[SubjectResponse], dependencies=[Depends(AnyAuthenticatedUser)])
async def list_subjects(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[SubjectResponse]:
    items = await AcademicService(db).list_subjects(skip=skip, limit=limit)
    return [SubjectResponse.from_orm_obj(i) for i in items]


@router.get("/subjects/{subject_id}", response_model=SubjectResponse, dependencies=[Depends(AnyAuthenticatedUser)])
async def get_subject(subject_id: UUID, db: AsyncSession = Depends(get_db)) -> SubjectResponse:
    return SubjectResponse.from_orm_obj(await AcademicService(db).get_subject(subject_id))


@router.patch("/subjects/{subject_id}", response_model=SubjectResponse, dependencies=[Depends(AdminOnly)])
async def update_subject(subject_id: UUID, body: SubjectUpdate, db: AsyncSession = Depends(get_db)) -> SubjectResponse:
    return SubjectResponse.from_orm_obj(await AcademicService(db).update_subject(subject_id, body))


@router.delete("/subjects/{subject_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_subject(subject_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await AcademicService(db).delete_subject(subject_id)
