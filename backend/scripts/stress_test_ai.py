#!/usr/bin/env python
"""
AI Grading Stress Test — "Midnight Deadline" scenario.

Simulates multiple students submitting an assignment simultaneously and the
Celery worker processing all AI grading tasks in parallel across the
Codespace → Render Redis hybrid-cloud link.

Flow per student:
  1. Login as student  → JWT
  2. Fetch student profile → student_id (UUID)
  3. POST /assignments/{id}/submit?student_id={uuid}&file_url=... → submission
  4. POST /assignments/submissions/{sub_id}/grade-ai  (staff token) → 202

Then polls until every submission reaches status=graded or times out.

Usage (from /workspaces/FinalYear_Projec/backend):
    python scripts/stress_test_ai.py
    python scripts/stress_test_ai.py --concurrent 5
    python scripts/stress_test_ai.py --keep        # skip cleanup
    python scripts/stress_test_ai.py --base-url http://localhost:8000/api/v1

Known API constraints honoured by this script:
  - submit: student_id is a QUERY PARAM, not JSON body
  - grade-ai: requires StaffOrAdmin role (staff token used)
  - Each student may only have ONE submission per assignment (409 on duplicate)
  - New throwaway assignment created per run → clean state, no 409 conflicts
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import httpx
except ImportError:
    import sys
    print("httpx required: pip install httpx")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
DEFAULT_BASE_URL = "https://lms-api-ukhs.onrender.com/api/v1"
STAFF_USERNAME   = "staff.alice"
STAFF_PASSWORD   = "StaffPass123!"
POLL_INTERVAL    = 5       # seconds between status polls
POLL_TIMEOUT     = 120     # seconds before giving up on a task
SUBMIT_TIMEOUT   = httpx.Timeout(60.0, connect=30.0)  # generous for free-tier wake-ups

# All 10 seeded students — each gets their own submission slot
STUDENTS = [
    ("stu.emma",     "StudPass123!"),
    ("stu.liam",     "StudPass123!"),
    ("stu.olivia",   "StudPass123!"),
    ("stu.noah",     "StudPass123!"),
    ("stu.ava",      "StudPass123!"),
    ("stu.ethan",    "StudPass123!"),
    ("stu.sophia",   "StudPass123!"),
    ("stu.mason",    "StudPass123!"),
    ("stu.isabella", "StudPass123!"),
    ("stu.james",    "StudPass123!"),
]

# ── ANSI colours ───────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def ui_ok(msg: str)   -> None: print(f"{GREEN}  ✓  {RESET}{msg}")
def ui_fail(msg: str) -> None: print(f"{RED}  ✗  {RESET}{msg}")
def ui_info(msg: str) -> None: print(f"{CYAN}  ·  {RESET}{msg}")
def ui_warn(msg: str) -> None: print(f"{YELLOW}  ⚠  {RESET}{msg}")
def ui_head(msg: str) -> None: print(f"\n{BOLD}{msg}{RESET}")


# ── Auth helpers ───────────────────────────────────────────────────────────────

async def get_token(client: httpx.AsyncClient, username: str, password: str) -> str:
    resp = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def get_student_profile_id(
    client: httpx.AsyncClient, student_token: str
) -> str:
    """Return the student_profile UUID (not user UUID) for this token's user."""
    resp = await client.get(
        "/students/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    resp.raise_for_status()
    return resp.json()["id"]


# ── Setup: create a one-shot stress-test assignment ───────────────────────────

async def create_stress_assignment(
    client: httpx.AsyncClient, staff_token: str
) -> dict[str, Any]:
    """
    Create a fresh assignment for this run so every student starts clean
    (no 409 Conflict from previous runs).
    """
    # We need a subject_id that belongs to staff.alice (Introduction to Programming)
    resp = await client.get(
        "/academic/subjects",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    resp.raise_for_status()
    subjects = resp.json()

    # Find a subject taught by a CS staff member (any will do)
    subject_id = subjects[0]["id"] if subjects else None
    if not subject_id:
        raise RuntimeError("No subjects found — run seed_production.py first")

    # Get staff profile id
    resp = await client.get(
        "/staff/me",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    resp.raise_for_status()
    staff_id = resp.json()["id"]

    payload = {
        "title": f"__stress_test__{datetime.now(timezone.utc).strftime('%H%M%S')}__",
        "description": (
            "Write 2-3 sentences explaining the benefits of asynchronous programming "
            "in modern web architectures. Reference at least one real-world example."
        ),
        "subject_id": str(subject_id),
        "staff_id": str(staff_id),
        "status": "published",
        # Strip tzinfo — the DateTime column has no timezone support (naive UTC expected)
        "due_date": (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None).isoformat(),
        "max_score": 100.0,
        "ai_grading_enabled": True,
    }
    resp = await client.post(
        "/assignments",
        json=payload,
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    resp.raise_for_status()
    assignment = resp.json()
    ui_ok(f"Stress assignment created: {assignment['id'][:8]}...  ({assignment['title']})")
    return assignment


async def cleanup(
    client: httpx.AsyncClient,
    staff_token: str,
    assignment_id: str,
) -> None:
    """Delete the throwaway assignment (cascades to all submissions)."""
    resp = await client.delete(
        f"/assignments/{assignment_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    if resp.status_code == 204:
        ui_ok(f"Cleanup: stress assignment {assignment_id[:8]}... deleted")
    else:
        ui_warn(f"Cleanup partial: HTTP {resp.status_code}")


# ── Per-student submission pipeline ───────────────────────────────────────────

async def student_pipeline(
    client: httpx.AsyncClient,
    student_username: str,
    student_password: str,
    staff_token: str,
    assignment_id: str,
    index: int,
) -> dict[str, Any]:
    """
    Full pipeline for one student:
      login → get profile_id → submit → enqueue AI grade
    Returns a result dict.
    """
    result: dict[str, Any] = {
        "student": student_username,
        "index": index,
        "submission_id": None,
        "assignment_id": assignment_id,
        "submitted": False,
        "grading_queued": False,
        "grading_status": "pending",
        "score": None,
        "ai_feedback": None,
        "error": None,
        "submit_ms": None,
        "queue_ms": None,
        "grade_ms": None,
    }

    try:
        # Step 1: login
        student_token = await get_token(client, student_username, student_password)

        # Step 2: get student profile id (needed as query param on submit)
        student_profile_id = await get_student_profile_id(client, student_token)

        # Step 3: submit — student_id is a QUERY PARAM, file_url simulates inline answer
        essay_text = (
            f"Student {index + 1} submission: Async programming improves scalability "
            f"by allowing non-blocking I/O operations. In FastAPI, this means thousands "
            f"of concurrent connections without spawning a thread per request — "
            f"demonstrated clearly in Node.js event-loop architecture."
        )
        # Pass text inline as file_url (AI prompt includes it as-is)
        t0 = time.perf_counter()
        sub_resp = await client.post(
            f"/assignments/{assignment_id}/submit",
            params={
                "student_id": student_profile_id,
                "file_url": essay_text,
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
        result["submit_ms"] = round((time.perf_counter() - t0) * 1000)

        if sub_resp.status_code != 201:
            result["error"] = f"submit HTTP {sub_resp.status_code}: {sub_resp.text[:200]}"
            ui_fail(f"[{student_username}] submission failed: {result['error']}")
            return result

        submission = sub_resp.json()
        result["submission_id"] = submission["id"]
        result["assignment_id"] = assignment_id
        result["submitted"] = True
        ui_ok(f"[{student_username}] submitted  sub={submission['id'][:8]}...  ({result['submit_ms']}ms)")

        # Step 4: enqueue AI grading  — StaffOrAdmin required
        t1 = time.perf_counter()
        grade_resp = await client.post(
            f"/assignments/submissions/{submission['id']}/grade-ai",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        result["queue_ms"] = round((time.perf_counter() - t1) * 1000)

        if grade_resp.status_code == 202:
            result["grading_queued"] = True
            ui_info(f"[{student_username}] AI task enqueued ({result['queue_ms']}ms)")
        else:
            result["error"] = f"grade-ai HTTP {grade_resp.status_code}: {grade_resp.text[:200]}"
            ui_warn(f"[{student_username}] grade-ai: {result['error']}")

    except Exception as exc:
        result["error"] = str(exc)
        ui_fail(f"[{student_username}] pipeline error: {exc}")

    return result


# ── Poll for completion ────────────────────────────────────────────────────────

async def poll_until_graded(
    client: httpx.AsyncClient,
    staff_token: str,
    results: list[dict[str, Any]],
) -> None:
    """Poll every POLL_INTERVAL seconds until all queued jobs are graded or timeout."""
    pending = {
        r["submission_id"]: r
        for r in results
        if r["grading_queued"] and r["submission_id"]
    }
    if not pending:
        ui_warn("No submissions queued for grading — nothing to poll")
        return

    headers = {"Authorization": f"Bearer {staff_token}"}
    deadline = time.time() + POLL_TIMEOUT
    graded_count = 0
    total = len(pending)

    ui_head(f"Polling {total} AI grading tasks (timeout={POLL_TIMEOUT}s)...")

    # Track when each task started
    task_start: dict[str, float] = {sid: time.time() for sid in pending}

    while pending and time.time() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        done_this_round: list[str] = []

        for sub_id, result in pending.items():
            try:
                resp = await client.get(
                    f"/assignments/submissions/{sub_id}",
                    headers=headers,
                )
                if resp.status_code != 200:
                    # Try alternate route
                    resp = await client.get(
                        f"/assignments/{result.get('assignment_id', 'unknown')}/submissions/{sub_id}",
                        headers=headers,
                    )
                if resp.status_code != 200:
                    continue  # not available yet, try next poll
                sub = resp.json()
            except Exception:
                continue

            if sub.get("status") in ("graded", "returned"):
                elapsed = round((time.time() - task_start[sub_id]) * 1000)
                result["grading_status"] = sub["status"]
                result["score"] = sub.get("score")
                result["ai_feedback"] = sub.get("ai_feedback", "")
                result["grade_ms"] = elapsed
                graded_count += 1
                done_this_round.append(sub_id)

                feedback_preview = (result["ai_feedback"] or "")[:80]
                ui_ok(
                    f"GRADED [{result['student']}] "
                    f"score={result['score']}  "
                    f"time={elapsed}ms  "
                    f'feedback="{feedback_preview}..."'
                )

        for sid in done_this_round:
            del pending[sid]

        if pending:
            elapsed_total = round(time.time() - (deadline - POLL_TIMEOUT))
            ui_info(
                f"Waiting... {graded_count}/{total} graded "
                f"({len(pending)} pending, {elapsed_total}s elapsed)"
            )

    # Mark any remaining as timed out
    for sub_id, result in pending.items():
        result["grading_status"] = "timeout"
        ui_warn(f"[{result['student']}] TIMEOUT after {POLL_TIMEOUT}s — task still pending")


# ── Submission status lookup (alternate path) ──────────────────────────────────

async def fetch_submission(
    client: httpx.AsyncClient,
    staff_token: str,
    submission_id: str,
) -> dict | None:
    """Try to fetch a submission via the submissions sub-route."""
    resp = await client.get(
        f"/assignments/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    if resp.status_code == 200:
        return resp.json()
    return None


# ── Analysis report ───────────────────────────────────────────────────────────

def print_report(results: list[dict[str, Any]], wall_time: float) -> None:
    ui_head("=" * 60)
    ui_head(" STRESS TEST RESULTS")

    submitted      = [r for r in results if r["submitted"]]
    queued         = [r for r in results if r["grading_queued"]]
    graded         = [r for r in results if r["grading_status"] == "graded"]
    timed_out      = [r for r in results if r["grading_status"] == "timeout"]
    failed         = [r for r in results if r["error"]]

    print(f"\n  Total students   : {len(results)}")
    print(f"  Submitted        : {GREEN}{len(submitted)}{RESET}")
    print(f"  Tasks queued     : {GREEN}{len(queued)}{RESET}")
    print(f"  AI graded        : {GREEN}{len(graded)}{RESET}")
    print(f"  Timed out        : {YELLOW}{len(timed_out)}{RESET}")
    print(f"  Errors           : {RED}{len(failed)}{RESET}")
    print(f"  Wall time        : {wall_time:.1f}s")

    if graded:
        submit_times = [r["submit_ms"] for r in graded if r["submit_ms"]]
        grade_times  = [r["grade_ms"]  for r in graded if r["grade_ms"]]
        scores       = [r["score"]     for r in graded if r["score"] is not None]

        if submit_times:
            print(f"\n  {BOLD}Submission latency:{RESET}")
            print(f"    min={min(submit_times)}ms  max={max(submit_times)}ms  "
                  f"avg={sum(submit_times)//len(submit_times)}ms")

        if grade_times:
            print(f"\n  {BOLD}AI grading latency (queue→complete):{RESET}")
            print(f"    min={min(grade_times)}ms  max={max(grade_times)}ms  "
                  f"avg={sum(grade_times)//len(grade_times)}ms")

        if scores:
            print(f"\n  {BOLD}AI-assigned scores:{RESET}")
            print(f"    min={min(scores):.1f}  max={max(scores):.1f}  "
                  f"avg={sum(scores)/len(scores):.1f}")

    if failed:
        print(f"\n  {RED}{BOLD}Errors:{RESET}")
        for r in failed:
            print(f"    [{r['student']}] {r['error']}")

    # Senior analysis ---------------------
    print(f"\n{BOLD}Senior Analysis:{RESET}")

    all_succeeded = len(graded) == len(results)
    rate_limited  = any("429" in str(r.get("error", "")) for r in results)

    if all_succeeded and not rate_limited:
        print(f"  {GREEN}✓{RESET} Backpressure OK — all {len(graded)} tasks processed by worker")
        print(f"  {GREEN}✓{RESET} OpenRouter free tier handled burst without 429s")
        print(f"  {GREEN}✓{RESET} Hybrid-cloud link (Codespace worker ↔ Render Redis) stable")
    elif rate_limited:
        print(f"  {YELLOW}⚠{RESET}  OpenRouter 429 detected — add Celery retry_backoff:")
        print(f"      @celery_app.task(bind=True, max_retries=3, default_retry_delay=10)")
    if timed_out:
        print(f"  {YELLOW}⚠{RESET}  {len(timed_out)} task(s) timed out — worker may be down or disconnected")
        print(f"       → Re-run: bash backend/scripts/start_worker.sh")
    if not all_succeeded and not timed_out:
        print(f"  {RED}✗{RESET}  Some submissions failed — check errors above")

    print()


# ── Main ───────────────────────────────────────────────────────────────────────

async def run(
    base_url: str,
    concurrent: int,
    keep: bool,
    skip_poll: bool,
) -> int:
    print(f"\n{BOLD}{'='*60}")
    print(f" LMS AI Grading Stress Test — Midnight Deadline Scenario")
    print(f" Base URL  : {base_url}")
    print(f" Students  : {concurrent} (parallel submissions)")
    print(f" Date/Time : {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}{RESET}")

    students_subset = STUDENTS[:concurrent]
    assignment_id: str | None = None

    async with httpx.AsyncClient(base_url=base_url, timeout=SUBMIT_TIMEOUT) as client:

        # ── Setup ──────────────────────────────────────────────────────────────
        ui_head("Phase 1 — Login & Setup")
        try:
            staff_token = await get_token(client, STAFF_USERNAME, STAFF_PASSWORD)
            ui_ok(f"Staff login OK ({STAFF_USERNAME})")
        except httpx.HTTPStatusError as exc:
            ui_fail(f"Staff login failed: HTTP {exc.response.status_code} — {exc.response.text[:200]}")
            return 1
        except Exception as exc:
            ui_fail(f"Staff login failed: {type(exc).__name__}: {exc}")
            return 1

        try:
            assignment = await create_stress_assignment(client, staff_token)
            assignment_id = assignment["id"]
        except Exception as exc:
            ui_fail(f"Could not create stress assignment: {exc}")
            return 1

        # ── Parallel submission flood ──────────────────────────────────────────
        ui_head(f"Phase 2 — Parallel Submissions ({concurrent} students simultaneously)")
        t_start = time.time()

        tasks = [
            student_pipeline(
                client,
                username, password,
                staff_token,
                assignment_id,
                idx,
            )
            for idx, (username, password) in enumerate(students_subset)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        results_list: list[dict[str, Any]] = list(results)

        # Attach assignment_id to each result (for poll path)
        for r in results_list:
            r["assignment_id"] = assignment_id

        flood_time = time.time() - t_start
        submitted = sum(1 for r in results_list if r["submitted"])
        queued    = sum(1 for r in results_list if r["grading_queued"])
        ui_info(f"Flood complete in {flood_time:.2f}s — {submitted}/{concurrent} submitted, {queued} grading tasks enqueued")

        # ── Poll for completion ────────────────────────────────────────────────
        if not skip_poll:
            ui_head("Phase 3 — Waiting for AI Grading Results")
            await poll_until_graded(client, staff_token, results_list)

        wall_time = time.time() - t_start

        # ── Cleanup ──────────────────────────────────────────────────────────
        if not keep and assignment_id:
            ui_head("Phase 4 — Cleanup")
            await cleanup(client, staff_token, assignment_id)

    # ── Report ────────────────────────────────────────────────────────────────
    print_report(results_list, wall_time)

    failed = sum(1 for r in results_list if r["error"] or r["grading_status"] == "timeout")
    return 0 if failed == 0 else 1


def main() -> None:
    import sys
    parser = argparse.ArgumentParser(
        description="LMS AI Grading Stress Test — Midnight Deadline scenario"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        choices=range(1, 11),
        metavar="N",
        help="Number of simultaneous students (1-10, default: 10)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Skip cleanup — keep stress assignment and submissions in DB for inspection",
    )
    parser.add_argument(
        "--no-poll",
        action="store_true",
        help="Skip polling phase — just submit and queue, don't wait for results",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(run(
        base_url=args.base_url,
        concurrent=args.concurrent,
        keep=args.keep,
        skip_poll=args.no_poll,
    )))


if __name__ == "__main__":
    main()
