---
name: lms-frontend-execplan
description: "Author a self-contained executable specification (ExecPlan) for Phase 8 — the Next.js 15 frontend of the School Management System LMS. Use when writing frontend implementation plans, scaffolding Next.js components, generating frontend architecture docs, specifying API client or state management patterns, or detailing WebSocket integration. Trigger phrases: write frontend execplan, author frontend spec, create frontend implementation plan, spec frontend component, draft frontend architecture, plan frontend phase, frontend websocket, tanstack query hooks, zustand store spec, ai grade ui, role dashboard spec."
argument-hint: "Describe what needs to be specified for the frontend (e.g. 'Step 8.7 useNotificationStream hook', 'Admin analytics dashboard page', 'Axios 401 refresh interceptor', 'AIGradeStatus component with Framer Motion')."
user-invocable: true
---

# LMS Frontend ExecPlan Authoring Skill

You are a Professional Modern Software Web Application and AI/ML Engineer. You author executable
specifications ("ExecPlans") for the Phase 8 Next.js 15 frontend of the School Management System.
A stateless coding agent must be able to implement any spec you produce without prior context.

## When to Use

- Writing step-level implementation plans for Phase 8 frontend work
- Specifying a new component, hook, page, or API module in `frontend/src/`
- Producing frontend architecture design documents
- Handing off implementation work to the **LMS Modernization Architectural Design Pattern Planner (FrontEnd)** agent

## Core Contract

A frontend ExecPlan must be:

- **Self-contained** — no external blog links or docs. Embed all required knowledge in your own words.
- **Unambiguous** — resolve every fork in the plan yourself. Do not say "choose one approach"; say which one and why.
- **Evidence-capturing** — include expected terminal output, TypeScript types, or short diffs that prove each step succeeded.
- **Backend-synchronized** — every API call references the exact method, path, and response schema from the live backend.

## Procedure

### Step 1 — Read Before Writing

Before drafting a single word of the plan:

1. Read `backend/docs/FRONTEND_ARCHITECTURE.md` in full — the canonical Phase 8 ExecPlan.
2. Read `backend/docs/ARCHITECTURE.md` — backend component responsibilities and data flow.
3. Read `backend/docs/SECURITY.md` — token storage rules and RBAC constraints.
4. Read `backend/docs/API_DESIGN.md` — error envelope, pagination, auth header conventions.
5. Inventory `frontend/src/` if it exists (do not assume any file is present).
6. Identify which of the 19 Phase 8 steps the current spec belongs to.

### Step 2 — Choose the Right ExecPlan Type

| Type | When to use | Required sections |
|------|-------------|-------------------|
| **Step Plan** | Implementing one of the 19 numbered steps end-to-end | Goal, Backend Contract, Implementation, Verification |
| **Component Spec** | A single React component or hook | Props interface, State shape, Backend calls, Render spec |
| **Page Spec** | A full Next.js App Router page | Route, Role guard, Data needs (TanStack Query keys), Layout |
| **Integration Spec** | Cross-cutting: API client, stores, key factory | Dependency graph, Init order, Error handling |

### Step 3 — Required Sections for All Frontend ExecPlans

```
# ExecPlan: <short title> (Phase 8 Step N)

## Context
<Why this spec exists. Which Phase 8 step it implements. What backend endpoints it consumes.>
<List every assumption. State what frontend files exist and what their current state is.>

## Backend Contract
<Exact HTTP methods, paths, request bodies, and response shapes consumed by this spec.>
<Include the TypeScript type from src/types/models.ts that maps to each response.>

## Scope
<Exact list of files to create or modify. Nothing else changes.>

## Design Decisions
<For each non-obvious choice: option chosen, one-sentence rationale.>

## Implementation
<Complete file content. Never truncate. Never use "// ... rest of file ..." comments.>

## Verification
<Exact command. Expected stdout. Expected browser behavior.>

## Acceptance Criteria
<Checklist of observable outcomes. Every item verifiable by running a command or using the browser.>
```

### Step 4 — Flesh Out Steps

For each implementation step:

- Write the **complete file content** — not a summary, not a skeleton with TODOs.
- For shell commands, include expected stdout:

  ```
  Expected output:
      ✓ compiled client and server successfully in 2.3s
  ```

- For TypeScript types, include the full interface definition, not just the changed field.
- For Zod schemas, verify each field name exactly matches the Pydantic `BaseModel` field name.

### Step 5 — Frontend-Specific Quality Checks

Before saving the plan, verify all of the following:

| # | Check | How to verify |
|---|-------|---------------|
| F1 | All API paths start with `/api/v1/` | Grep the spec for any bare path |
| F2 | Access token comes from `useAuthStore.getState().accessToken` — never localStorage | Grep for `localStorage.get` |
| F3 | Refresh token is stored via Zustand `persist` only | Confirm `partialize` excludes `accessToken` |
| F4 | Datetime fields do NOT get `"Z"` appended | Grep for `.toISOString()` in form submit handlers |
| F5 | WS `"pong"` message is filtered before `JSON.parse()` | Confirm `if (event.data === "pong") return;` |
| F6 | No `any` TypeScript type | Grep for `: any` |
| F7 | All imports use `@/` alias, not relative `../../` | Grep for `from "../` |
| F8 | `"use client"` directive present on all interactive components | Grep for `useState\|useEffect` without preceding `"use client"` |
| F9 | Axios calls go through `apiClient`, not native `fetch` | Grep for `fetch(` in `src/` |
| F10 | `toast.success` fired from `useNotificationStream`, not from the submit handler | Confirm toast is in the WS event handler |

### Step 6 — Save and Announce

- Save the plan to `backend/plans/phase8-<slug>.md`.
- Summarize: which Phase 8 step it covers, what files it creates/modifies, and what will be true when done.
- Ask: "Ready to execute? Type **Yes, execute `<filename>`** to proceed."

---

## Failure Modes to Avoid

| Anti-pattern | Fix |
|---|---|
| "Call the API to get the user" | Write the exact method: `apiClient.get<UserResponse>("/auth/me")` |
| "Handle the 401 case" | Specify: interceptor retries once after refresh; on second 401 calls `clearSession()` and redirects to `/login` |
| "Add proper TypeScript types" | Write the complete interface; don't defer to the reader |
| Component spec without `"use client"` | All components using hooks need the directive on line 1 |
| Zod schema with camelCase field names | Pydantic uses snake_case — `student_id`, not `studentId` |
| Form submits Date object | Must serialize: `date.toISOString().replace("Z", "")` |
| WS reconnection not handled | `onerror` must call `ws.close()` and rely on React effect cleanup + remount |

---

## Architecture Reference (embedded — do not fetch externally)

### Technology Stack (pinned versions)

| Package | Version | Role |
|---------|---------|------|
| `next` | `^15.3` | App Router, Server Components |
| `react` | `^19.0` | UI runtime |
| `typescript` | `^5.4` | Type safety |
| `tailwindcss` | `^3.4` | Utility CSS |
| `framer-motion` | `^11.x` | Score reveal + layout animations |
| `@tanstack/react-query` | `^5.40` | Server state cache |
| `zustand` | `^4.5` | Client/global state |
| `axios` | `^1.7` | HTTP client |
| `axios-retry` | `^4.x` | 503 retry for Render cold starts |
| `react-hook-form` | `^7.52` | Form management |
| `zod` | `^3.23` | Schema validation |
| `recharts` | `^2.12` | Grade/attendance charts |
| `@tremor/react` | `^3.18` | Admin metric cards |
| `@tanstack/react-table` | `^8.17` | Data tables |
| `cmdk` | `^1.0` | Cmd+K palette |
| `sonner` | `^1.5` | Toast notifications |
| `next-themes` | `^0.3` | Dark/light mode |
| `lucide-react` | `^0.400` | Icons |

### Frontend Directory Overview

```
frontend/src/
├── app/                    # Next.js 15 App Router pages + layouts
│   ├── (auth)/login/       # Public login page
│   └── (dashboard)/        # Protected shell — auth check in layout.tsx
│       ├── admin/          # Admin-only pages
│       ├── staff/          # Staff-only pages
│       └── student/        # Student-only pages
├── components/
│   ├── ui/                 # Shadcn/UI primitives (auto-generated)
│   ├── layout/             # Sidebar, Header, NotificationBell, CommandMenu
│   ├── auth/               # LoginForm, AuthGuard
│   ├── grades/             # AIGradeStatus, GradeCard
│   ├── assignments/        # AssignmentForm, SubmissionUpload
│   ├── quizzes/            # QuizForm, QuestionBuilder, QuizAttemptUI
│   ├── analytics/          # AttendanceChart, GradeTrendChart, DepartmentStats
│   └── shared/             # DataTable, PaginationBar, LoadingSpinner, ErrorBoundary
├── lib/
│   ├── api/                # apiClient + per-domain API call functions
│   ├── hooks/              # useNotificationStream, useAuth, usePermission
│   ├── query/keys.ts       # TanStack Query key factory (all 11 domains)
│   ├── schemas/            # Zod schemas matching Pydantic models
│   └── utils/              # cn(), dates.ts, errors.ts
├── stores/
│   ├── authStore.ts        # Access token (memory), refresh token (persisted), user
│   └── uiStore.ts          # Sidebar open, theme
└── types/
    ├── api.ts              # PaginatedResponse<T>, APIError envelope
    └── models.ts           # TypeScript mirrors of all Pydantic Response schemas
```

### WebSocket Event Protocol

All events pushed by the FastAPI `manager.send_to_user()` follow this shape:

```typescript
interface WSEvent {
  type: "submission:graded" | "attempt:graded" | "notification:new" | "item:update";
  payload: Record<string, unknown>;
}
```

| Event type | Payload fields | Action |
|-----------|---------------|--------|
| `submission:graded` | `submission_id`, `assignment_id`, `score`, `ai_feedback` | invalidate submission + assignment queries; toast.success |
| `attempt:graded` | `attempt_id`, `quiz_id`, `score` | invalidate attempt + quiz queries; toast.success |
| `notification:new` | _(none required)_ | invalidate `notifications.mine()` query |
| `item:update` | _(any)_ | broad `queryClient.invalidateQueries()` |

### Async Handshake Summary

```
User submits → POST /assignments/{id}/submit → 201
  → AIGradeStatus renders pending badge (Loader2 spin)
Celery grades → manager.send_to_user(student_id, {type:"submission:graded", ...})
  → useNotificationStream invalidates query
  → GET /assignments/submissions/{id} re-fetched
  → AIGradeStatus animates score reveal (Framer Motion spring 300/24)
  → sonner toast fires
```

### Phase 8 Step Sequence

| Step | Deliverable |
|------|-------------|
| 8.1 | Bootstrap Next.js 15 |
| 8.2 | Install all dependencies |
| 8.3 | `.env.local` configuration |
| 8.4 | Axios client + interceptors |
| 8.5 | Zustand stores |
| 8.6 | TanStack Query key factory |
| 8.7 | `useNotificationStream` hook |
| 8.8 | `AIGradeStatus` component |
| 8.9 | `AuthGuard` component |
| 8.10 | Zod validation schemas |
| 8.11 | TypeScript model types |
| 8.12 | Dashboard shell layout |
| 8.13 | Role-aware Sidebar |
| 8.14 | Login page |
| 8.15 | Admin dashboard |
| 8.16 | Staff dashboard |
| 8.17 | Student dashboard |
| 8.18 | Cmd+K command palette |
| 8.19 | Production build verification |
