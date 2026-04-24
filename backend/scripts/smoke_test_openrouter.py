#!/usr/bin/env python
"""
Live API smoke test — OpenRouter model routing.

Tests all three task-model assignments by making real network calls to OpenRouter.
Requires OPENAI_API_KEY and OPENAI_BASE_URL to be set in backend/.env.

Usage:
    python scripts/smoke_test_openrouter.py
    python scripts/smoke_test_openrouter.py --model essay      # single task
    python scripts/smoke_test_openrouter.py --model quiz reason # subset
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Callable

# ── path bootstrap ────────────────────────────────────────────────────────────
# Allow running from both backend/ and project root.
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
sys.path.insert(0, str(_BACKEND))

# Load .env before importing settings
from dotenv import load_dotenv
load_dotenv(_BACKEND / ".env")

from app.core.config import get_settings
from app.services.ai_agent import AIGradingAgent

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg: str)   -> str: return f"{GREEN}  ✓  {RESET}{msg}"
def fail(msg: str) -> str: return f"{RED}  ✗  {RESET}{msg}"
def info(msg: str) -> str: return f"{CYAN}  ·  {RESET}{msg}"
def head(msg: str) -> str: return f"\n{BOLD}{msg}{RESET}"


# ── individual smoke probes ───────────────────────────────────────────────────

async def probe_essay(agent: AIGradingAgent) -> tuple[bool, str, float]:
    settings = get_settings()
    model = settings.GRADING_ESSAY_MODEL
    t0 = time.perf_counter()
    result = await agent.grade_essay(
        assignment_title="The Impact of Climate Change on Agriculture",
        assignment_description="Discuss how rising temperatures affect crop yields globally.",
        file_url=None,
    )
    elapsed = time.perf_counter() - t0
    passed = bool(result and len(result.strip()) > 10)
    return passed, result.strip()[:200] if result else "(empty)", elapsed


async def probe_quiz(agent: AIGradingAgent) -> tuple[bool, str, float]:
    settings = get_settings()
    model = settings.GRADING_QUIZ_MODEL
    t0 = time.perf_counter()
    is_correct, marks, feedback = await agent.grade_short_answer(
        question_text="What is the powerhouse of the cell?",
        correct_answer="Mitochondria",
        student_answer="The mitochondria is the powerhouse of the cell.",
        marks=5.0,
    )
    elapsed = time.perf_counter() - t0
    passed = is_correct is True and marks > 0.0
    summary = f"correct={is_correct}, marks={marks:.1f}, feedback='{feedback[:120]}'"
    return passed, summary, elapsed


async def probe_reason(agent: AIGradingAgent) -> tuple[bool, str, float]:
    settings = get_settings()
    model = settings.REASONING_MODEL
    t0 = time.perf_counter()
    result = await agent.analyse_student_performance(
        student_name="John Doe",
        subject="Mathematics",
        scores=[45.0, 55.0, 62.0, 70.0, 78.0],
    )
    elapsed = time.perf_counter() - t0
    passed = bool(result and len(result.strip()) > 10)
    return passed, result.strip()[:200] if result else "(empty)", elapsed


# ── probe registry ────────────────────────────────────────────────────────────

PROBES: dict[str, tuple[str, str, Callable]] = {
    #  key     display label               model-env-var              async fn
    "essay":  ("Essay grading",  "GRADING_ESSAY_MODEL",  probe_essay),
    "quiz":   ("Quiz grading",   "GRADING_QUIZ_MODEL",   probe_quiz),
    "reason": ("Reasoning/analytics", "REASONING_MODEL", probe_reason),
}


# ── runner ────────────────────────────────────────────────────────────────────

async def run_smoke_tests(selected: list[str]) -> int:
    settings = get_settings()
    agent = AIGradingAgent()

    # ── preflight ─────────────────────────────────────────────────────────────
    print(head("OpenRouter Smoke Test — Preflight"))
    if not settings.OPENAI_API_KEY:
        print(fail("OPENAI_API_KEY is not set. Aborting."))
        return 1
    print(info(f"Base URL  : {settings.OPENAI_BASE_URL or 'https://api.openai.com (default)'}"))
    print(info(f"API key   : {settings.OPENAI_API_KEY[:12]}...{settings.OPENAI_API_KEY[-4:]}"))
    print(info(f"Running   : {', '.join(selected)}"))

    results: list[tuple[str, bool, str, float, str]] = []  # (key, passed, summary, elapsed, model)

    for key in selected:
        label, model_env, probe_fn = PROBES[key]
        model_name = getattr(settings, model_env, "?")
        print(head(f"{label}"))
        print(info(f"Model ({model_env}): {model_name}"))

        try:
            passed, summary, elapsed = await probe_fn(agent)
        except Exception as exc:
            passed, summary, elapsed = False, f"Exception: {exc}", 0.0

        results.append((key, passed, summary, elapsed, model_name))

        if passed:
            print(ok(f"Response ({elapsed:.2f}s): {summary}"))
        else:
            print(fail(f"Response ({elapsed:.2f}s): {summary}"))

    # ── summary ───────────────────────────────────────────────────────────────
    print(head("─" * 60))
    print(head("Summary"))
    total = len(results)
    passed_count = sum(1 for _, p, *_ in results if p)

    for key, passed, summary, elapsed, model in results:
        label = PROBES[key][0]
        icon = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {icon}  {label:<28} {elapsed:.2f}s  [{model}]")

    print()
    if passed_count == total:
        print(f"{GREEN}{BOLD}All {total}/{total} probes passed.{RESET}")
    else:
        print(f"{RED}{BOLD}{passed_count}/{total} probes passed.{RESET}")

    return 0 if passed_count == total else 1


def parse_args() -> list[str]:
    parser = argparse.ArgumentParser(description="Live OpenRouter smoke test")
    parser.add_argument(
        "--model",
        nargs="*",
        choices=list(PROBES.keys()),
        default=list(PROBES.keys()),
        metavar="TASK",
        help="Which task probes to run: essay, quiz, reason (default: all)",
    )
    return parser.parse_args().model


if __name__ == "__main__":
    selected = parse_args()
    exit_code = asyncio.run(run_smoke_tests(selected))
    sys.exit(exit_code)
