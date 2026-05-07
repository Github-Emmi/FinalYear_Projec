"""Admin AI Chat endpoint — personal assistant for the admin panel.

Backed by OpenRouter (openai SDK). Receives conversation history + new message,
enriches context with live platform analytics + full DB records, then returns
the AI reply.
"""

from __future__ import annotations

import logging
from typing import List, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AdminOnly, get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/chat", tags=["admin-chat"])
_settings = get_settings()

# ── Request / Response schemas ──────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


# ── Live DB records context ──────────────────────────────────────────────────


async def _fetch_records_context(db: AsyncSession) -> str:
    """Query DB for real records and return a formatted context block."""
    from app.models.staff import StaffProfile
    from app.models.student import StudentProfile
    from app.models.academic import ClassRoom, Department, Subject
    from app.models.assignment import Assignment

    lines: list[str] = []

    # ── Staff ──────────────────────────────────────────────────────────────
    try:
        staff_rows = (
            await db.execute(
                select(StaffProfile)
                .where(StaffProfile.is_deleted.is_(False))
                .options(
                    selectinload(StaffProfile.user),
                    selectinload(StaffProfile.department),
                )
                .order_by(StaffProfile.created_at)
            )
        ).scalars().all()

        lines.append("Staff members:")
        if staff_rows:
            for s in staff_rows:
                u = s.user
                name = f"{u.first_name or ''} {u.last_name or ''}".strip() if u else "Unknown"
                dept = s.department.name if s.department else "No dept"
                desig = s.designation or "Staff"
                lines.append(f"  - {name} | {desig} | {dept} | {u.email if u else ''}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Chat context: staff fetch failed: %s", exc)
        lines.append("Staff members: (unavailable)")

    # ── Students ───────────────────────────────────────────────────────────
    try:
        student_rows = (
            await db.execute(
                select(StudentProfile)
                .where(StudentProfile.is_deleted.is_(False))
                .options(
                    selectinload(StudentProfile.user),
                    selectinload(StudentProfile.classroom),
                )
                .order_by(StudentProfile.created_at)
                .limit(200)  # cap to keep prompt size sane
            )
        ).scalars().all()

        lines.append("\nStudents:")
        if student_rows:
            for s in student_rows:
                u = s.user
                name = f"{u.first_name or ''} {u.last_name or ''}".strip() if u else "Unknown"
                cls = s.classroom.name if s.classroom else "No class"
                roll = s.roll_number or "—"
                lines.append(f"  - {name} | Roll: {roll} | Class: {cls} | {u.email if u else ''}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Chat context: student fetch failed: %s", exc)
        lines.append("\nStudents: (unavailable)")

    # ── Departments ────────────────────────────────────────────────────────
    try:
        dept_rows = (
            await db.execute(
                select(Department)
                .where(Department.is_deleted.is_(False))
                .order_by(Department.name)
            )
        ).scalars().all()

        lines.append("\nDepartments:")
        if dept_rows:
            for d in dept_rows:
                lines.append(f"  - {d.name}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Chat context: department fetch failed: %s", exc)

    # ── Classrooms ─────────────────────────────────────────────────────────
    try:
        cr_rows = (
            await db.execute(
                select(ClassRoom)
                .where(ClassRoom.is_deleted.is_(False))
                .options(selectinload(ClassRoom.department))
                .order_by(ClassRoom.name)
            )
        ).scalars().all()

        lines.append("\nClassrooms:")
        if cr_rows:
            for c in cr_rows:
                dept = c.department.name if c.department else "—"
                lines.append(f"  - {c.name} | Dept: {dept}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Chat context: classroom fetch failed: %s", exc)

    # ── Subjects ───────────────────────────────────────────────────────────
    try:
        subj_rows = (
            await db.execute(
                select(Subject)
                .where(Subject.is_deleted.is_(False))
                .options(
                    selectinload(Subject.staff).selectinload(StaffProfile.user),
                    selectinload(Subject.classroom),
                )
                .order_by(Subject.name)
            )
        ).scalars().all()

        lines.append("\nSubjects:")
        if subj_rows:
            for s in subj_rows:
                cls = s.classroom.name if s.classroom else "—"
                staff_u = s.staff.user if s.staff else None
                teacher = (
                    f"{staff_u.first_name or ''} {staff_u.last_name or ''}".strip()
                    if staff_u else "Unassigned"
                )
                lines.append(f"  - {s.name} | Class: {cls} | Teacher: {teacher}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Chat context: subject fetch failed: %s", exc)

    # ── Recent assignments ─────────────────────────────────────────────────
    try:
        asgn_rows = (
            await db.execute(
                select(Assignment)
                .where(Assignment.is_deleted.is_(False))
                .order_by(Assignment.created_at.desc())
                .limit(20)
            )
        ).scalars().all()

        lines.append("\nRecent assignments (latest 20):")
        if asgn_rows:
            for a in asgn_rows:
                due = str(a.due_date)[:10] if getattr(a, "due_date", None) else "—"
                lines.append(f"  - {a.title} | Due: {due}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Chat context: assignment fetch failed: %s", exc)

    return "\n".join(lines)


# ── System prompt factory ────────────────────────────────────────────────────

_SYSTEM_TEMPLATE = """You are an intelligent personal AI assistant embedded inside the School Management System (LMS) admin panel.

You have FULL READ ACCESS to the live database. Actual records are provided below — use them to give precise, accurate answers.

Platform stats (live counts):
{analytics_block}

Live database records:
{records_block}

Logged-in admin: {admin_name} ({admin_email})

Your capabilities:
- Answer questions about specific students, staff, classrooms, subjects, assignments, etc.
- List names, emails, departments, classes — pulling from the records above
- Give data-driven insights (e.g. "Staff in dept X", "Students in class Y")
- Explain platform features and workflows

Guidelines:
- Use the records above to answer questions directly. Never say "I don't have access" — you do.
- If asked to list staff or students, list them from the data above.
- If the admin asks to modify data, explain that changes must be made through the relevant admin pages.
- Be concise and accurate. Use bullet points for lists.
- Do not expose passwords or security tokens.
"""


def _build_analytics_block(stats: dict) -> str:
    return (
        f"- Total users: {stats.get('total_users', 'N/A')}\n"
        f"- Total students: {stats.get('total_students', 'N/A')}\n"
        f"- Total staff: {stats.get('total_staff', 'N/A')}\n"
        f"- Total classrooms: {stats.get('total_classrooms', 'N/A')}\n"
        f"- Total subjects: {stats.get('total_subjects', 'N/A')}\n"
        f"- Total assignments: {stats.get('total_assignments', 'N/A')}\n"
        f"- Total quizzes: {stats.get('total_quizzes', 'N/A')}\n"
        f"- Submissions today: {stats.get('submissions_today', 'N/A')}\n"
        f"- Pending AI grading queue: {stats.get('grading_queue', 'N/A')}"
    )


# ── Endpoint ─────────────────────────────────────────────────────────────────


@router.post("", response_model=ChatResponse, dependencies=[Depends(AdminOnly)])
async def admin_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Send a message to the admin AI assistant and receive a reply."""

    if not _settings.resolved_openai_key:
        return ChatResponse(
            reply="AI assistant is unavailable: OPENAI_API_KEY / OPENROUTER_API_KEY is not configured."
        )

    # Fetch live platform stats + full DB records for context
    try:
        stats = await AnalyticsService(db).platform_summary()
    except Exception:
        stats = {}

    try:
        records_block = await _fetch_records_context(db)
    except Exception as exc:
        logger.warning("Chat context: records fetch failed: %s", exc)
        records_block = "(records unavailable)"

    analytics_block = _build_analytics_block(stats)
    admin_name = f"{current_user.first_name} {current_user.last_name}".strip()
    system_prompt = _SYSTEM_TEMPLATE.format(
        analytics_block=analytics_block,
        records_block=records_block,
        admin_name=admin_name,
        admin_email=current_user.email,
    )

    # Build message list for the model
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in body.history[-20:]:  # cap history at 20 turns
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": body.message})

    # Call the model
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=_settings.resolved_openai_key,
            base_url=_settings.OPENAI_BASE_URL or None,
        )
        model = getattr(_settings, "OPENAI_MODEL", None) or "openai/gpt-4o-mini"
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=768,
        )
        reply = response.choices[0].message.content or "No response generated."
    except Exception as exc:
        logger.error("Admin chat AI call failed: %s", exc)
        reply = f"Sorry, I encountered an error: {exc}"

    return ChatResponse(reply=reply)
