"""Staff AI Chat endpoint — personal assistant scoped to the logged-in staff member.

Backed by OpenRouter (openai SDK). Receives conversation history + new message,
enriches context with the staff member's own live data (subjects, students,
assignments, quizzes, attendance, leave), then returns the AI reply.
"""

from __future__ import annotations

import logging
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/staff/chat", tags=["staff-chat"])
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


# ── Live context builder ─────────────────────────────────────────────────────


async def _fetch_staff_context(db: AsyncSession, user: User) -> str:
    """Query DB for data specific to this staff member and return a formatted block."""
    from app.models.staff import StaffProfile
    from app.models.academic import ClassRoom, Subject
    from app.models.student import StudentProfile
    from app.models.assignment import Assignment, AssignmentSubmission
    from app.models.assessment import Quiz, QuizAttempt
    from app.models.leave import LeaveRequest

    lines: list[str] = []

    # ── Staff profile ──────────────────────────────────────────────────────
    staff_profile = None
    try:
        result = await db.execute(
            select(StaffProfile)
            .where(StaffProfile.user_id == user.id, StaffProfile.is_deleted.is_(False))
            .options(
                selectinload(StaffProfile.department),
            )
        )
        staff_profile = result.scalar_one_or_none()

        if staff_profile:
            dept = staff_profile.department.name if staff_profile.department else "No department"
            desig = staff_profile.designation or "Staff"
            lines.append(f"Your profile: {user.first_name} {user.last_name} | {desig} | {dept} | {user.email}")
        else:
            lines.append("Your profile: (no staff profile found)")
    except Exception as exc:
        logger.warning("Staff chat context: profile fetch failed: %s", exc)
        lines.append("Your profile: (unavailable)")

    if staff_profile is None:
        return "\n".join(lines)

    staff_id = staff_profile.id

    # ── Subjects this staff teaches ────────────────────────────────────────
    try:
        subj_rows = (
            await db.execute(
                select(Subject)
                .where(Subject.staff_id == staff_id, Subject.is_deleted.is_(False))
                .options(selectinload(Subject.classroom))
                .order_by(Subject.name)
            )
        ).scalars().all()

        classroom_ids = list({s.classroom_id for s in subj_rows if s.classroom_id})

        lines.append(f"\nSubjects you teach ({len(subj_rows)}):")
        if subj_rows:
            for s in subj_rows:
                cls = s.classroom.name if s.classroom else "—"
                lines.append(f"  - {s.name} | Class: {cls}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Staff chat context: subject fetch failed: %s", exc)
        classroom_ids = []
        lines.append("\nSubjects: (unavailable)")

    # ── Students in your classrooms ────────────────────────────────────────
    try:
        if classroom_ids:
            student_rows = (
                await db.execute(
                    select(StudentProfile)
                    .where(
                        StudentProfile.classroom_id.in_(classroom_ids),
                        StudentProfile.is_deleted.is_(False),
                    )
                    .options(
                        selectinload(StudentProfile.user),
                        selectinload(StudentProfile.classroom),
                    )
                    .order_by(StudentProfile.classroom_id)
                    .limit(300)
                )
            ).scalars().all()

            lines.append(f"\nStudents in your classrooms ({len(student_rows)}):")
            for s in student_rows:
                u = s.user
                name = f"{u.first_name or ''} {u.last_name or ''}".strip() if u else "Unknown"
                cls = s.classroom.name if s.classroom else "—"
                roll = s.roll_number or "—"
                lines.append(f"  - {name} | Roll: {roll} | Class: {cls}")
        else:
            lines.append("\nStudents: (no classrooms assigned)")
    except Exception as exc:
        logger.warning("Staff chat context: students fetch failed: %s", exc)
        lines.append("\nStudents: (unavailable)")

    # ── Assignments you created ────────────────────────────────────────────
    try:
        asgn_rows = (
            await db.execute(
                select(Assignment)
                .where(Assignment.staff_id == staff_id, Assignment.is_deleted.is_(False))
                .order_by(Assignment.created_at.desc())
                .limit(50)
            )
        ).scalars().all()

        lines.append(f"\nYour assignments ({len(asgn_rows)} most recent):")
        if asgn_rows:
            for a in asgn_rows:
                due = str(a.due_date)[:10] if getattr(a, "due_date", None) else "—"
                status_val = getattr(a, "status", "—")
                lines.append(f"  - {a.title} | Due: {due} | Status: {status_val}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Staff chat context: assignment fetch failed: %s", exc)
        lines.append("\nAssignments: (unavailable)")

    # ── Submissions pending grading ────────────────────────────────────────
    try:
        if asgn_rows:
            asgn_ids = [a.id for a in asgn_rows]
            pending_subs = (
                await db.execute(
                    select(AssignmentSubmission)
                    .where(
                        AssignmentSubmission.assignment_id.in_(asgn_ids),
                        AssignmentSubmission.score.is_(None),
                        AssignmentSubmission.is_deleted.is_(False),
                    )
                )
            ).scalars().all()

            lines.append(f"\nPending grading: {len(pending_subs)} submission(s) awaiting your review")
    except Exception as exc:
        logger.warning("Staff chat context: pending submissions fetch failed: %s", exc)

    # ── Quizzes you created ────────────────────────────────────────────────
    try:
        quiz_rows = (
            await db.execute(
                select(Quiz)
                .where(Quiz.staff_id == staff_id, Quiz.is_deleted.is_(False))
                .order_by(Quiz.created_at.desc())
                .limit(20)
            )
        ).scalars().all()

        lines.append(f"\nYour quizzes ({len(quiz_rows)}):")
        if quiz_rows:
            for q in quiz_rows:
                lines.append(f"  - {q.title}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Staff chat context: quiz fetch failed: %s", exc)

    # ── Attendance sessions you ran ────────────────────────────────────────
    try:
        from app.models.attendance import AttendanceSession

        att_rows = (
            await db.execute(
                select(AttendanceSession)
                .where(
                    AttendanceSession.staff_id == staff_id,
                    AttendanceSession.is_deleted.is_(False),
                )
                .order_by(AttendanceSession.date.desc())
                .limit(30)
            )
        ).scalars().all()

        lines.append(f"\nYour attendance sessions (last {len(att_rows)}):")
        if att_rows:
            for a in att_rows:
                date_str = str(a.date)[:10]
                lines.append(f"  - {date_str} | Status: {getattr(a, 'status', '—')}")
        else:
            lines.append("  (none)")
    except Exception as exc:
        logger.warning("Staff chat context: attendance fetch failed: %s", exc)

    # ── Your leave requests ────────────────────────────────────────────────
    try:
        leave_rows = (
            await db.execute(
                select(LeaveRequest)
                .where(
                    LeaveRequest.staff_id == staff_id,
                    LeaveRequest.is_deleted.is_(False),
                )
                .order_by(LeaveRequest.created_at.desc())
                .limit(10)
            )
        ).scalars().all()

        if leave_rows:
            lines.append(f"\nYour leave requests ({len(leave_rows)}):")
            for lr in leave_rows:
                start = str(getattr(lr, "start_date", "—"))[:10]
                end = str(getattr(lr, "end_date", "—"))[:10]
                status_val = getattr(lr, "status", "—")
                lines.append(f"  - {start} to {end} | Status: {status_val}")
    except Exception as exc:
        logger.warning("Staff chat context: leave fetch failed: %s", exc)

    return "\n".join(lines)


# ── System prompt ────────────────────────────────────────────────────────────

_SYSTEM_TEMPLATE = """You are an intelligent personal AI assistant for {staff_name}, a {designation} at this school.

You have READ ACCESS to {staff_name}'s live data from the School Management System (LMS). The actual records are provided below — use them to give precise, personalised answers.

Your staff member's live data:
{records_block}

Current session context:
- Academic session: {session_info}

Your capabilities:
- Answer questions about {staff_name}'s students, classes, assignments, quizzes, and attendance
- Identify students who may need attention (e.g. low attendance, missing submissions)
- Summarise classroom performance and trends from the data above
- Help plan lessons, assessments, or feedback strategies
- Explain LMS features and workflows relevant to staff

Guidelines:
- Use the records above to answer questions directly. Never say "I don't have access" — you do.
- If asked about a specific student, reference their name, roll number, and class from the data.
- If asked to modify data, explain that changes must be made through the relevant staff pages.
- Be concise and supportive. Use bullet points for lists.
- Address the staff member warmly by first name when appropriate.
- Do not expose passwords or security tokens.
"""


# ── Endpoint ─────────────────────────────────────────────────────────────────


@router.post("", response_model=ChatResponse)
async def staff_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Send a message to the staff AI assistant and receive a personalised reply."""

    # Only staff (and admin acting as staff) can use this
    if current_user.role not in ("staff", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff members can use the staff assistant.",
        )

    if not _settings.resolved_openai_key:
        return ChatResponse(
            reply="AI assistant is unavailable: OPENAI_API_KEY / OPENROUTER_API_KEY is not configured."
        )

    try:
        records_block = await _fetch_staff_context(db, current_user)
    except Exception as exc:
        logger.warning("Staff chat: context fetch failed: %s", exc)
        records_block = "(context unavailable)"

    staff_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or "Staff"

    # Attempt to derive designation from profile block
    designation = "teacher"
    if "profile:" in records_block:
        try:
            profile_line = [l for l in records_block.splitlines() if l.startswith("Your profile:")][0]
            parts = profile_line.split("|")
            if len(parts) >= 2:
                designation = parts[1].strip()
        except Exception:
            pass

    system_prompt = _SYSTEM_TEMPLATE.format(
        staff_name=staff_name,
        designation=designation,
        records_block=records_block,
        session_info="Current academic session",
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in body.history[-20:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": body.message})

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
        logger.error("Staff chat AI call failed: %s", exc)
        reply = f"Sorry, I encountered an error: {exc}"

    return ChatResponse(reply=reply)
