"""Modular AI grading agent backed by OpenRouter.

Design:
- Single async client shared across the process (lazy init).
- Model is selected per task type — swap in .env without code changes.
- Falls back silently when OPENAI_API_KEY is not configured (dev/test).

Task types:
  essay   → GRADING_ESSAY_MODEL   (instruction-following, GPT-4o-mini class)
  quiz    → GRADING_QUIZ_MODEL    (fast + cheap, llama-3.3-70b free tier)
  reason  → REASONING_MODEL       (DeepSeek-R1 for complex analysis)

Usage::

    from app.services.ai_agent import ai_agent

    feedback = await ai_agent.grade_essay(assignment_title, submission_text)
    result   = await ai_agent.grade_short_answer(question_text, correct_answer, student_answer)
"""

from __future__ import annotations

import logging
from typing import Literal

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

TaskType = Literal["essay", "quiz", "reason"]

_MODEL_MAP: dict[TaskType, str] = {
    "essay": _settings.GRADING_ESSAY_MODEL,
    "quiz": _settings.GRADING_QUIZ_MODEL,
    "reason": _settings.REASONING_MODEL,
}


def _get_client():
    """Lazy-init AsyncOpenAI client pointed at OpenRouter (or OpenAI if base_url unset)."""
    from openai import AsyncOpenAI  # lazy — not all workers need it at startup

    return AsyncOpenAI(
        api_key=_settings.resolved_openai_key,
        base_url=_settings.OPENAI_BASE_URL or None,
    )


async def _call(system: str, user: str, task: TaskType) -> str:
    """Send a single-turn completion and return the text content."""
    if not _settings.resolved_openai_key:
        logger.warning("OPENAI_API_KEY / OPENROUTER_API_KEY not set — AI grading skipped")
        return ""

    model = _MODEL_MAP[task]
    client = _get_client()

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content or ""


class AIGradingAgent:
    """Stateless agent — all state lives in the DB, not here."""

    # ── Assignment / essay grading ─────────────────────────────────────────────

    async def grade_essay(
        self,
        assignment_title: str,
        assignment_description: str | None,
        file_url: str | None,
    ) -> str:
        """Return 2-3 sentence feedback for an assignment submission."""
        system = (
            "You are an expert educator grading student assignment submissions. "
            "Provide brief, constructive feedback (2-3 sentences) on quality and completeness. "
            "Be encouraging but honest."
        )
        user = (
            f"Assignment: {assignment_title}\n"
            f"Description: {assignment_description or 'N/A'}\n"
            f"Submitted file: {file_url or 'N/A'}\n\n"
            "Grade this submission with concise feedback."
        )
        return await _call(system, user, "essay")

    # ── Quiz short-answer grading ──────────────────────────────────────────────

    async def grade_short_answer(
        self,
        question_text: str,
        correct_answer: str | None,
        student_answer: str,
        marks: float,
    ) -> tuple[bool, float, str]:
        """Return (is_correct, marks_earned, feedback) for a short-answer question.

        The model returns JSON: {"correct": bool, "marks": float, "feedback": str}
        Falls back to (False, 0.0, "") on parse error.
        """
        import json

        system = (
            "You are grading a student's short-answer quiz response. "
            "Return ONLY valid JSON with keys: correct (bool), marks (float), feedback (str). "
            "Be concise and fair."
        )
        user = (
            f"Question: {question_text}\n"
            f"Expected answer: {correct_answer or 'N/A'}\n"
            f"Student answer: {student_answer}\n"
            f"Maximum marks: {marks}\n\n"
            'Return JSON: {"correct": true/false, "marks": 0.0, "feedback": "..."}'
        )

        raw = await _call(system, user, "quiz")
        if not raw:
            return False, 0.0, ""

        try:
            # Strip markdown code fences if present
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            is_correct = bool(data.get("correct", False))
            marks_earned = min(float(data.get("marks", 0.0)), marks)
            feedback = str(data.get("feedback", ""))
            return is_correct, marks_earned, feedback
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("AI grade parse failed: %s | raw=%r", exc, raw)
            return False, 0.0, raw[:200]  # return raw text as feedback fallback

    # ── Analytics / reasoning ──────────────────────────────────────────────────

    async def analyse_student_performance(
        self,
        student_name: str,
        subject: str,
        scores: list[float],
    ) -> str:
        """Return a short performance analysis paragraph using the reasoning model."""
        system = (
            "You are an educational data analyst. "
            "Analyse the student's performance trend and suggest 1-2 specific improvements."
        )
        user = (
            f"Student: {student_name}\n"
            f"Subject: {subject}\n"
            f"Recent scores (%): {scores}\n\n"
            "Write a 2-3 sentence analysis."
        )
        return await _call(system, user, "reason")


# Module-level singleton — import and use directly
ai_agent = AIGradingAgent()
