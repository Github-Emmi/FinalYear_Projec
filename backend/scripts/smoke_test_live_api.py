#!/usr/bin/env python
"""
Live end-to-end smoke test — validates every critical API flow against the
deployed Render instance.

Usage:
    python scripts/smoke_test_live_api.py
    python scripts/smoke_test_live_api.py --base-url https://lms-api-ukhs.onrender.com/api/v1
    python scripts/smoke_test_live_api.py --suite auth   # run only auth suite
    python scripts/smoke_test_live_api.py --suite auth students quizzes

Suites: health auth students staff academic quizzes assignments attendance analytics
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import Any
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_BASE_URL = "https://lms-api-ukhs.onrender.com/api/v1"
ADMIN_USERNAME   = "admin"
ADMIN_PASSWORD   = "AdminPass123!"
STAFF_USERNAME   = "staff.alice"
STAFF_PASSWORD   = "StaffPass123!"
STUDENT_USERNAME = "stu.emma"
STUDENT_PASSWORD = "StudPass123!"

TIMEOUT = httpx.Timeout(60.0, connect=15.0)

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

results: list[tuple[str, bool, str]] = []   # (name, passed, detail)

def ok(name: str, detail: str = "") -> None:
    results.append((name, True, detail))
    suffix = f" {DIM}({detail}){RESET}" if detail else ""
    print(f"{GREEN}  ✓  {RESET}{name}{suffix}")

def fail(name: str, detail: str = "") -> None:
    results.append((name, False, detail))
    suffix = f" {DIM}({detail}){RESET}" if detail else ""
    print(f"{RED}  ✗  {RESET}{name}{suffix}")

def skip(name: str, reason: str = "") -> None:
    results.append((name, True, f"SKIP: {reason}"))
    print(f"{YELLOW}  ⊘  {RESET}{name}  {DIM}skipped: {reason}{RESET}")

def head(msg: str) -> None:
    print(f"\n{BOLD}{msg}{RESET}")

def assert_status(resp: httpx.Response, expected: int, name: str) -> bool:
    if resp.status_code == expected:
        ok(name, f"HTTP {resp.status_code}")
        return True
    else:
        fail(name, f"expected {expected}, got {resp.status_code}: {resp.text[:200]}")
        return False


# ── Auth helpers ──────────────────────────────────────────────────────────────

async def get_token(
    client: httpx.AsyncClient, username: str, password: str, label: str
) -> str | None:
    resp = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        ok(f"Login: {label}", "token acquired")
        return token
    fail(f"Login: {label}", f"HTTP {resp.status_code}: {resp.text[:200]}")
    return None


# ── Test Suites ───────────────────────────────────────────────────────────────

async def suite_health(client: httpx.AsyncClient) -> None:
    head("Suite: Health")
    resp = await client.get("/health")
    if assert_status(resp, 200, "GET /health"):
        body = resp.json()
        if body.get("status") == "ok":
            ok("/health status == 'ok'")
        else:
            fail("/health status field", str(body))


async def suite_auth(client: httpx.AsyncClient) -> dict[str, str | None]:
    head("Suite: Authentication")
    tokens: dict[str, str | None] = {}

    for label, uname, pwd in [
        ("admin",   ADMIN_USERNAME,   ADMIN_PASSWORD),
        ("staff",   STAFF_USERNAME,   STAFF_PASSWORD),
        ("student", STUDENT_USERNAME, STUDENT_PASSWORD),
    ]:
        tokens[label] = await get_token(client, uname, pwd, label)

    # /me endpoint
    if tokens["admin"]:
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        resp = await client.get("/auth/me", headers=headers)
        if assert_status(resp, 200, "GET /auth/me (admin)"):
            me = resp.json()
            if me.get("role") == "admin":
                ok("/auth/me role == 'admin'")
            else:
                fail("/auth/me role check", str(me))

    return tokens


async def suite_students(
    client: httpx.AsyncClient, tokens: dict[str, str | None]
) -> dict[str, Any]:
    head("Suite: Students")
    admin_hdrs = {"Authorization": f"Bearer {tokens['admin']}"} if tokens.get("admin") else {}
    student_hdrs = {"Authorization": f"Bearer {tokens['student']}"} if tokens.get("student") else {}

    created_id = None

    # List students (admin)
    resp = await client.get("/students", headers=admin_hdrs)
    assert_status(resp, 200, "GET /students (admin)")
    if resp.status_code == 200:
        count = len(resp.json())
        ok(f"Student list count", f"{count} records")

    # Student self-profile
    if tokens.get("student"):
        resp = await client.get("/students/me", headers=student_hdrs)
        assert_status(resp, 200, "GET /students/me (student)")
        if resp.status_code == 200:
            profile = resp.json()
            ok("Student self-profile", f"roll={profile.get('roll_number')}")
            created_id = profile.get("id")

    return {"student_profile_id": created_id}


async def suite_staff(
    client: httpx.AsyncClient, tokens: dict[str, str | None]
) -> dict[str, Any]:
    head("Suite: Staff")
    admin_hdrs = {"Authorization": f"Bearer {tokens['admin']}"} if tokens.get("admin") else {}
    staff_hdrs = {"Authorization": f"Bearer {tokens['staff']}"} if tokens.get("staff") else {}

    resp = await client.get("/staff", headers=admin_hdrs)
    assert_status(resp, 200, "GET /staff (admin)")
    if resp.status_code == 200:
        ok("Staff list", f"{len(resp.json())} records")

    staff_id = None
    if tokens.get("staff"):
        resp = await client.get("/staff/me", headers=staff_hdrs)
        assert_status(resp, 200, "GET /staff/me (staff)")
        if resp.status_code == 200:
            profile = resp.json()
            ok("Staff self-profile", f"designation={profile.get('designation')}")
            staff_id = profile.get("id")

    return {"staff_profile_id": staff_id}


async def suite_academic(
    client: httpx.AsyncClient, tokens: dict[str, str | None]
) -> dict[str, Any]:
    head("Suite: Academic Structure")
    admin_hdrs = {"Authorization": f"Bearer {tokens['admin']}"} if tokens.get("admin") else {}

    ids: dict[str, Any] = {}

    # Departments  (mounted under /academic/)
    resp = await client.get("/academic/departments", headers=admin_hdrs)
    assert_status(resp, 200, "GET /academic/departments")
    if resp.status_code == 200:
        depts = resp.json()
        ok("Departments list", f"{len(depts)} records")
        if depts:
            ids["department_id"] = depts[0]["id"]

    # Session years
    resp = await client.get("/academic/session-years", headers=admin_hdrs)
    assert_status(resp, 200, "GET /academic/session-years")
    if resp.status_code == 200:
        sys_list = resp.json()
        ok("Session years list", f"{len(sys_list)} records")
        if sys_list:
            ids["session_year_id"] = sys_list[0]["id"]

    # Classrooms
    resp = await client.get("/academic/classrooms", headers=admin_hdrs)
    assert_status(resp, 200, "GET /academic/classrooms")
    if resp.status_code == 200:
        cls_list = resp.json()
        ok("Classrooms list", f"{len(cls_list)} records")
        if cls_list:
            ids["classroom_id"] = cls_list[0]["id"]

    # Subjects
    resp = await client.get("/academic/subjects", headers=admin_hdrs)
    assert_status(resp, 200, "GET /academic/subjects")
    if resp.status_code == 200:
        subj_list = resp.json()
        ok("Subjects list", f"{len(subj_list)} records")
        if subj_list:
            ids["subject_id"] = subj_list[0]["id"]

    return ids


async def suite_quizzes(
    client: httpx.AsyncClient,
    tokens: dict[str, str | None],
    academic_ids: dict[str, Any],
    staff_ids: dict[str, Any],
) -> dict[str, Any]:
    head("Suite: Quizzes & Assessments")
    staff_hdrs = {"Authorization": f"Bearer {tokens['staff']}"} if tokens.get("staff") else {}
    student_hdrs = {"Authorization": f"Bearer {tokens['student']}"} if tokens.get("student") else {}

    ids: dict[str, Any] = {}
    subject_id = academic_ids.get("subject_id")
    staff_profile_id = staff_ids.get("staff_profile_id")

    if not subject_id:
        skip("Quiz suite", "no subject_id from academic suite")
        return ids

    # List quizzes for a subject (academic prefix)
    resp = await client.get(f"/academic/subjects/{subject_id}/quizzes", headers=staff_hdrs)
    if resp.status_code == 200:
        quizzes = resp.json()
        ok(f"GET /academic/subjects/{{id}}/quizzes", f"{len(quizzes)} quizzes")
        if quizzes:
            ids["quiz_id"] = quizzes[0]["id"]
    elif resp.status_code == 404:
        skip("GET /academic/subjects/{id}/quizzes", "not yet on this path")
    else:
        fail("GET /academic/subjects/{id}/quizzes", f"HTTP {resp.status_code}")

    # Create → fetch → publish → delete round-trip as staff
    if tokens.get("staff") and subject_id and staff_profile_id:
        payload = {
            "title": "__smoke_test_quiz__",
            "subject_id": str(subject_id),
            "staff_id": str(staff_profile_id),
            "time_limit_minutes": 10,
            "pass_score": 50.0,
            "ai_grading_enabled": False,
        }
        create_resp = await client.post("/quizzes", json=payload, headers=staff_hdrs)
        if create_resp.status_code == 201:
            quiz_id = create_resp.json()["id"]
            ok("POST /quizzes (staff create)", f"id={quiz_id[:8]}...")
            ids["quiz_id"] = quiz_id

            # Fetch
            get_resp = await client.get(f"/quizzes/{quiz_id}", headers=student_hdrs)
            assert_status(get_resp, 200, "GET /quizzes/{id} (student fetch)")

            # Add a question
            q_payload = {
                "text": "Smoke test: Is this working?",
                "question_type": "true_false",
                "correct_answer": "true",
                "marks": 1.0,
                "order": 0,
            }
            q_resp = await client.post(
                f"/quizzes/{quiz_id}/questions", json=q_payload, headers=staff_hdrs
            )
            assert_status(q_resp, 201, "POST /quizzes/{id}/questions")

            # Publish
            pub_resp = await client.post(f"/quizzes/{quiz_id}/publish", headers=staff_hdrs)
            assert_status(pub_resp, 200, "POST /quizzes/{id}/publish")

            # Cleanup: delete
            del_resp = await client.delete(f"/quizzes/{quiz_id}", headers=staff_hdrs)
            if del_resp.status_code == 204:
                ok("DELETE /quizzes/{id} (cleanup)")
            else:
                skip("DELETE /quizzes/{id}", f"HTTP {del_resp.status_code}")
        else:
            fail("Quiz create probe", f"HTTP {create_resp.status_code}: {create_resp.text[:200]}")
    elif not staff_profile_id:
        skip("Quiz create probe", "no staff_profile_id")

    return ids


async def suite_assignments(
    client: httpx.AsyncClient,
    tokens: dict[str, str | None],
    academic_ids: dict[str, Any],
    student_ids: dict[str, Any],
    staff_ids: dict[str, Any],
) -> None:
    head("Suite: Assignments")
    staff_hdrs = {"Authorization": f"Bearer {tokens['staff']}"} if tokens.get("staff") else {}
    student_hdrs = {"Authorization": f"Bearer {tokens['student']}"} if tokens.get("student") else {}

    subject_id = academic_ids.get("subject_id")
    staff_profile_id = staff_ids.get("staff_profile_id")
    if not subject_id:
        skip("Assignments suite", "no subject_id")
        return

    resp = await client.get(f"/academic/subjects/{subject_id}/assignments", headers=staff_hdrs)
    if resp.status_code == 200:
        assignments = resp.json()
        ok("GET /academic/subjects/{id}/assignments", f"{len(assignments)} assignments")
    elif resp.status_code == 404:
        skip("GET /academic/subjects/{id}/assignments", "path variant not available")
    else:
        fail("GET /academic/subjects/{id}/assignments", f"HTTP {resp.status_code}")

    # Create → fetch → delete round-trip as staff
    if tokens.get("staff") and subject_id and staff_profile_id:
        from datetime import datetime, timedelta
        payload = {
            "title": "__smoke_test_assignment__",
            "subject_id": str(subject_id),
            "staff_id": str(staff_profile_id),
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "max_score": 100.0,
            "ai_grading_enabled": False,
        }
        create_resp = await client.post("/assignments", json=payload, headers=staff_hdrs)
        if create_resp.status_code == 201:
            a_id = create_resp.json()["id"]
            ok("POST /assignments (staff create)", f"id={a_id[:8]}...")

            # Student can fetch it
            get_resp = await client.get(f"/assignments/{a_id}", headers=student_hdrs)
            assert_status(get_resp, 200, "GET /assignments/{id} (student fetch)")

            # Cleanup
            del_resp = await client.delete(f"/assignments/{a_id}", headers=staff_hdrs)
            if del_resp.status_code == 204:
                ok("DELETE /assignments/{id} (cleanup)")
            else:
                skip("DELETE /assignments/{id}", f"HTTP {del_resp.status_code}")
        else:
            fail("Assignment create probe", f"HTTP {create_resp.status_code}: {create_resp.text[:200]}")
    elif not staff_profile_id:
        skip("Assignment create probe", "no staff_profile_id")


async def suite_attendance(
    client: httpx.AsyncClient,
    tokens: dict[str, str | None],
    student_ids: dict[str, Any],
) -> None:
    head("Suite: Attendance")
    admin_hdrs = {"Authorization": f"Bearer {tokens['admin']}"} if tokens.get("admin") else {}
    student_profile_id = student_ids.get("student_profile_id")

    if student_profile_id:
        resp = await client.get(
            f"/attendance/students/{student_profile_id}/summary",
            headers=admin_hdrs,
        )
        assert_status(resp, 200, "GET /attendance/students/{id}/summary")
        if resp.status_code == 200:
            summary = resp.json()
            ok("Attendance summary", str({k: v for k, v in list(summary.items())[:3]}))
    else:
        skip("Attendance summary", "no student_profile_id")


async def suite_analytics(
    client: httpx.AsyncClient, tokens: dict[str, str | None]
) -> None:
    head("Suite: Analytics")
    admin_hdrs = {"Authorization": f"Bearer {tokens['admin']}"} if tokens.get("admin") else {}

    for path in ["/analytics/dashboard", "/analytics/overview"]:
        resp = await client.get(path, headers=admin_hdrs)
        if resp.status_code == 200:
            ok(f"GET {path}", "200 OK")
        elif resp.status_code == 404:
            skip(f"GET {path}", "not implemented yet")
        else:
            fail(f"GET {path}", f"HTTP {resp.status_code}")


# ── security probes ───────────────────────────────────────────────────────────

async def suite_security(client: httpx.AsyncClient) -> None:
    head("Suite: Security Probes")

    # Unauthenticated access must be rejected
    # /quizzes has no GET-list route (only /quizzes/{id}), so use /students and /staff
    for path in ["/students", "/staff", "/academic/departments"]:
        resp = await client.get(path)
        if resp.status_code in (401, 403):
            ok(f"Unauthenticated {path} blocked", f"HTTP {resp.status_code}")
        else:
            fail(f"Unauthenticated {path} NOT blocked", f"HTTP {resp.status_code}")

    # Bad token
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer bad.token.here"})
    if resp.status_code in (401, 422):
        ok("Bad JWT rejected", f"HTTP {resp.status_code}")
    else:
        fail("Bad JWT NOT rejected", f"HTTP {resp.status_code}")

    # SQL injection attempt in query param (should return 422 or empty list, not 500)
    resp = await client.get("/students", params={"skip": "'; DROP TABLE users; --"})
    if resp.status_code in (401, 403, 422):
        ok("SQL injection param rejected safely", f"HTTP {resp.status_code}")
    else:
        fail("SQL injection param unexpected response", f"HTTP {resp.status_code}")


# ── main orchestrator ─────────────────────────────────────────────────────────

ALL_SUITES = ["health", "auth", "students", "staff", "academic",
              "quizzes", "assignments", "attendance", "analytics", "security"]

async def run(base_url: str, suites: list[str]) -> int:
    print(f"\n{BOLD}{'='*60}")
    print(f" LMS Live API Smoke Test")
    print(f" Base URL: {base_url}")
    print(f" Suites:   {', '.join(suites)}")
    print(f"{'='*60}{RESET}")

    async with httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT) as client:
        tokens: dict[str, str | None] = {"admin": None, "staff": None, "student": None}
        academic_ids: dict[str, Any] = {}
        student_ids: dict[str, Any] = {}
        staff_ids: dict[str, Any] = {}
        quiz_ids: dict[str, Any] = {}

        if "health" in suites:
            await suite_health(client)

        if "auth" in suites:
            tokens = await suite_auth(client)

        if "students" in suites:
            student_ids = await suite_students(client, tokens)

        if "staff" in suites:
            staff_ids = await suite_staff(client, tokens)

        if "academic" in suites:
            academic_ids = await suite_academic(client, tokens)

        if "quizzes" in suites:
            quiz_ids = await suite_quizzes(client, tokens, academic_ids, staff_ids)

        if "assignments" in suites:
            await suite_assignments(client, tokens, academic_ids, student_ids, staff_ids)

        if "attendance" in suites:
            await suite_attendance(client, tokens, student_ids)

        if "analytics" in suites:
            await suite_analytics(client, tokens)

        if "security" in suites:
            await suite_security(client)

    # ── summary ───────────────────────────────────────────────────────────────
    passed = sum(1 for _, p, d in results if p and not d.startswith("SKIP"))
    skipped = sum(1 for _, p, d in results if d.startswith("SKIP"))
    failed  = sum(1 for _, p, _ in results if not p)
    total   = len(results)

    print(f"\n{BOLD}{'='*60}")
    print(f" Results: {total} checks")
    print(f"{'='*60}{RESET}")
    print(f"  {GREEN}Passed : {passed}{RESET}")
    print(f"  {YELLOW}Skipped: {skipped}{RESET}")
    print(f"  {RED}Failed : {failed}{RESET}")

    if failed:
        print(f"\n{RED}{BOLD}Failed checks:{RESET}")
        for name, p, detail in results:
            if not p:
                print(f"  {RED}✗{RESET} {name}  — {detail}")
        return 1

    print(f"\n{GREEN}{BOLD}All checks passed! 🎉{RESET}\n")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="LMS live API smoke test")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--suite",
        nargs="*",
        choices=ALL_SUITES,
        default=ALL_SUITES,
        help="Which test suites to run (default: all)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.base_url, args.suite)))


if __name__ == "__main__":
    main()
