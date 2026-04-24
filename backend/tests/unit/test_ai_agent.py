"""Unit tests for the modular AIGradingAgent service.

All tests mock the OpenAI client — no real API calls.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_mock_completion(content: str):
    """Build a minimal chat completion mock that looks like openai's response."""
    msg = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=msg)
    return SimpleNamespace(choices=[choice])


# ── grade_essay ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_grade_essay_returns_feedback():
    from app.services.ai_agent import AIGradingAgent

    agent = AIGradingAgent()
    mock_resp = _make_mock_completion("Good work overall, but needs more citations.")

    with (
        patch("app.services.ai_agent._settings") as mock_settings,
        patch("app.services.ai_agent._get_client") as mock_client_factory,
    ):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.GRADING_ESSAY_MODEL = "openai/gpt-4o-mini"
        mock_settings.GRADING_QUIZ_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
        mock_settings.REASONING_MODEL = "deepseek/deepseek-r1-distill-qwen-32b"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_factory.return_value = mock_client

        feedback = await agent.grade_essay(
            assignment_title="Essay on Climate Change",
            assignment_description="Discuss causes and effects",
            file_url="https://example.com/essay.pdf",
        )

    assert "Good work" in feedback


@pytest.mark.asyncio
async def test_grade_essay_no_api_key_returns_empty():
    from app.services.ai_agent import AIGradingAgent

    agent = AIGradingAgent()

    with patch("app.services.ai_agent._settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.GRADING_ESSAY_MODEL = "openai/gpt-4o-mini"
        mock_settings.GRADING_QUIZ_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
        mock_settings.REASONING_MODEL = "deepseek/deepseek-r1-distill-qwen-32b"

        feedback = await agent.grade_essay("Title", None, None)

    assert feedback == ""


# ── grade_short_answer ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_grade_short_answer_correct():
    from app.services.ai_agent import AIGradingAgent

    agent = AIGradingAgent()
    payload = json.dumps({"correct": True, "marks": 5.0, "feedback": "Spot on!"})
    mock_resp = _make_mock_completion(payload)

    with (
        patch("app.services.ai_agent._settings") as mock_settings,
        patch("app.services.ai_agent._get_client") as mock_client_factory,
    ):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.GRADING_ESSAY_MODEL = "openai/gpt-4o-mini"
        mock_settings.GRADING_QUIZ_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
        mock_settings.REASONING_MODEL = "deepseek/deepseek-r1-distill-qwen-32b"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_factory.return_value = mock_client

        is_correct, marks, feedback = await agent.grade_short_answer(
            question_text="What is photosynthesis?",
            correct_answer="Process by which plants make food using sunlight",
            student_answer="Plants use sunlight to make food",
            marks=5.0,
        )

    assert is_correct is True
    assert marks == 5.0
    assert "Spot on" in feedback


@pytest.mark.asyncio
async def test_grade_short_answer_exceeds_max_marks_capped():
    from app.services.ai_agent import AIGradingAgent

    agent = AIGradingAgent()
    # AI returns more marks than allowed
    payload = json.dumps({"correct": True, "marks": 99.0, "feedback": "Great!"})
    mock_resp = _make_mock_completion(payload)

    with (
        patch("app.services.ai_agent._settings") as mock_settings,
        patch("app.services.ai_agent._get_client") as mock_client_factory,
    ):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.GRADING_ESSAY_MODEL = "openai/gpt-4o-mini"
        mock_settings.GRADING_QUIZ_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
        mock_settings.REASONING_MODEL = "deepseek/deepseek-r1-distill-qwen-32b"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_factory.return_value = mock_client

        _, marks, _ = await agent.grade_short_answer("Q", "A", "A", marks=10.0)

    assert marks == 10.0  # capped to max


@pytest.mark.asyncio
async def test_grade_short_answer_malformed_json_fallback():
    from app.services.ai_agent import AIGradingAgent

    agent = AIGradingAgent()
    mock_resp = _make_mock_completion("Sorry, I cannot grade this.")  # not JSON

    with (
        patch("app.services.ai_agent._settings") as mock_settings,
        patch("app.services.ai_agent._get_client") as mock_client_factory,
    ):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.GRADING_ESSAY_MODEL = "openai/gpt-4o-mini"
        mock_settings.GRADING_QUIZ_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
        mock_settings.REASONING_MODEL = "deepseek/deepseek-r1-distill-qwen-32b"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_client_factory.return_value = mock_client

        is_correct, marks, feedback = await agent.grade_short_answer("Q", "A", "A", marks=5.0)

    assert is_correct is False
    assert marks == 0.0
    assert len(feedback) > 0  # raw text returned as feedback fallback


# ── model map ─────────────────────────────────────────────────────────────────

def test_task_model_map_keys():
    """Verify _MODEL_MAP covers all TaskType literals."""
    from app.services.ai_agent import _MODEL_MAP

    assert set(_MODEL_MAP.keys()) == {"essay", "quiz", "reason"}
