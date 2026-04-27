# ExecPlan: Phase 8 — Frontend Architecture
## Architecture: School Management System — Modern Frontend

---

## Context

This document is the canonical architecture specification for **Phase 8** of the School
Management System. Phases 1–7 delivered a production-grade FastAPI backend (async SQLAlchemy,
PostgreSQL 15, Redis, Celery, WebSockets) deployed on Render.com. The backend is fully tested,
stress-validated at 10/10 concurrent AI grading tasks, and exposes a stable OpenAPI contract.

Phase 8 delivers the **consumer-facing Next.js 15 frontend** that integrates with every
backend endpoint, handles all three role-based experiences (Admin, Staff, Student), and
implements the Async Handshake pattern for real-time AI grading feedback.

This ExecPlan is self-contained. A stateless agent can implement the entire frontend using
only this document and the repository working tree.

### Backend Integration Facts (do not fetch externally)

| Parameter | Value |
|-----------|-------|
| Base API URL | `https://lms-api-ukhs.onrender.com/api/v1` |
| WebSocket URL | `wss://lms-api-ukhs.onrender.com/api/v1/ws/notifications?token={JWT}` |
| Auth scheme | `Authorization: Bearer <access_token>` |
| Token claims | `{ sub: string, role: "admin\|staff\|student", exp: number, jti: string }` |
| Access token TTL | 30 minutes |
| Refresh token TTL | 7 days |
| WS keepalive | Send text frame `"ping"` every 25 s (Render LB idle timeout = 30 s) |
| Error envelope | `{ "error": { "code": string, "message": string, "details": {} } }` |
| Pagination envelope | `{ "items": [], "total": number, "page": number, "page_size": number, "pages": number }` |
| Date format | ISO 8601 without timezone suffix — `datetime` fields are UTC naive strings |

### Roles and Capabilities

| Role | Capabilities |
|------|-------------|
| `admin` | Full CRUD on all entities, user management, system analytics |
| `staff` | Manage assigned classroom, assignments, quizzes (exams), attendance; review AI grades |
| `student` | View own data, submit assignments and quizzes, view grades and notifications |

---

## Scope

### Files to Create

```
frontend/
├── .env.local                          # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL
├── .eslintrc.json                      # Extends next/core-web-vitals + strict TypeScript
├── next.config.ts                      # Next.js config — rewrites, image domains
├── tailwind.config.ts                  # Token extensions for school brand palette
├── tsconfig.json                       # Strict TypeScript
├── components.json                     # Shadcn/UI config
├── src/
│   ├── app/                            # Next.js 15 App Router
│   │   ├── layout.tsx                  # Root layout — providers, fonts, theme
│   │   ├── page.tsx                    # Public landing → redirects to /dashboard
│   │   ├── (auth)/
│   │   │   └── login/
│   │   │       └── page.tsx            # Login form
│   │   └── (dashboard)/
│   │       ├── layout.tsx              # Dashboard shell — sidebar + header
│   │       ├── page.tsx                # Role-aware redirect
│   │       ├── admin/
│   │       │   ├── page.tsx            # Admin overview
│   │       │   ├── users/
│   │       │   │   ├── page.tsx        # User management table
│   │       │   │   └── [id]/
│   │       │   │       └── page.tsx    # User detail / edit
│   │       │   ├── students/
│   │       │   │   └── page.tsx        # Student roster
│   │       │   ├── staff/
│   │       │   │   └── page.tsx        # Staff roster
│   │       │   ├── academic/
│   │       │   │   └── page.tsx        # Departments, classrooms, subjects
│   │       │   └── analytics/
│   │       │       └── page.tsx        # System analytics dashboard
│   │       ├── staff/
│   │       │   ├── page.tsx            # Staff overview
│   │       │   ├── assignments/
│   │       │   │   ├── page.tsx        # Assignment list + create
│   │       │   │   └── [id]/
│   │       │   │       └── page.tsx    # Submission review + AI grade display
│   │       │   ├── quizzes/
│   │       │   │   ├── page.tsx        # Quiz list + create
│   │       │   │   └── [id]/
│   │       │   │       └── page.tsx    # Quiz detail + question builder
│   │       │   ├── attendance/
│   │       │   │   └── page.tsx        # Attendance tracker
│   │       │   └── leave/
│   │       │       └── page.tsx        # Leave request review
│   │       └── student/
│   │           ├── page.tsx            # Student overview + grade snapshot
│   │           ├── assignments/
│   │           │   ├── page.tsx        # Assignment list
│   │           │   └── [id]/
│   │           │       └── page.tsx    # Submit + AI grade status
│   │           ├── quizzes/
│   │           │   ├── page.tsx        # Available quizzes
│   │           │   └── [id]/
│   │           │       └── page.tsx    # Quiz attempt UI
│   │           ├── attendance/
│   │           │   └── page.tsx        # Own attendance summary
│   │           └── leave/
│   │               └── page.tsx        # Apply for leave
│   ├── components/
│   │   ├── ui/                         # Shadcn/UI generated components (auto-populated)
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx             # Role-aware navigation sidebar
│   │   │   ├── Header.tsx              # Top bar — search, notifications bell, avatar
│   │   │   ├── NotificationBell.tsx    # Badge counter + dropdown
│   │   │   └── CommandMenu.tsx         # Cmd+K global search (cmdk)
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx           # React Hook Form + Zod login schema
│   │   │   └── AuthGuard.tsx           # HOC — enforces JWT + role presence
│   │   ├── grades/
│   │   │   ├── AIGradeStatus.tsx       # Pending/graded badge + score reveal animation
│   │   │   └── GradeCard.tsx           # Score display with Framer Motion slide-in
│   │   ├── assignments/
│   │   │   ├── AssignmentForm.tsx      # Create/edit assignment
│   │   │   └── SubmissionUpload.tsx    # File URL input + submit
│   │   ├── quizzes/
│   │   │   ├── QuizForm.tsx            # Create quiz form
│   │   │   ├── QuestionBuilder.tsx     # Add/edit MCQ + essay questions
│   │   │   └── QuizAttemptUI.tsx       # Timed quiz attempt interface
│   │   ├── analytics/
│   │   │   ├── AttendanceChart.tsx     # Recharts bar/line chart
│   │   │   ├── GradeTrendChart.tsx     # Recharts area chart
│   │   │   └── DepartmentStats.tsx     # Tremor metric cards
│   │   └── shared/
│   │       ├── DataTable.tsx           # TanStack Table v8 wrapper
│   │       ├── PaginationBar.tsx       # Prev/next with page params
│   │       ├── LoadingSpinner.tsx      # Full-page and inline spinners
│   │       └── ErrorBoundary.tsx       # React error boundary with retry
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts               # Axios instance + 401 refresh interceptor
│   │   │   ├── auth.ts                 # login(), refresh(), logout() functions
│   │   │   ├── users.ts                # User API calls
│   │   │   ├── students.ts             # Student API calls
│   │   │   ├── staff.ts                # Staff API calls
│   │   │   ├── academic.ts             # Academic entity API calls
│   │   │   ├── assignments.ts          # Assignment + submission API calls
│   │   │   ├── assessments.ts          # Quiz + attempt API calls
│   │   │   ├── attendance.ts           # Attendance session + record API calls
│   │   │   ├── leave.ts                # Leave request API calls
│   │   │   ├── notifications.ts        # Notification API calls
│   │   │   └── analytics.ts            # Analytics API calls
│   │   ├── hooks/
│   │   │   ├── useNotificationStream.ts # WebSocket hook — handles AI grade push
│   │   │   ├── useAuth.ts               # Auth state helpers
│   │   │   └── usePermission.ts         # Role-based access check hook
│   │   ├── query/
│   │   │   └── keys.ts                 # Centralized TanStack Query key factory
│   │   ├── schemas/
│   │   │   ├── auth.schema.ts          # Zod — login form validation
│   │   │   ├── assignment.schema.ts    # Zod — assignment create/update
│   │   │   ├── quiz.schema.ts          # Zod — quiz + question schemas
│   │   │   ├── student.schema.ts       # Zod — student profile schemas
│   │   │   └── leave.schema.ts         # Zod — leave request schema
│   │   └── utils/
│   │       ├── dates.ts                # Date formatting (no TZ suffix fix)
│   │       ├── cn.ts                   # Tailwind class merging (clsx + twMerge)
│   │       └── errors.ts               # API error normalizer
│   ├── stores/
│   │   ├── authStore.ts                # Zustand — user session, JWT tokens
│   │   └── uiStore.ts                  # Zustand — sidebar open, theme
│   └── types/
│       ├── api.ts                      # Response envelope types
│       └── models.ts                   # TypeScript mirrors of all Pydantic responses
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Next.js 15 App Router | Server Components reduce JS bundle for public pages; layouts map cleanly to role-based shells |
| Language | TypeScript strict mode | Mirrors Pydantic v2 contract; catches UUID/string confusion at compile time |
| Component library | Shadcn/UI + Radix UI | Unstyled primitives owned in-repo — no version lock, full accessibility built-in |
| Animations | Framer Motion | Best-in-class layout animations for score reveal and notification slide-in |
| Server state | TanStack Query v5 | Automatic background refetch, optimistic updates, and `invalidateQueries` integration with WebSocket push |
| Client/UI state | Zustand | Minimal, non-boilerplate store for sidebar toggle, theme, and JWT session |
| HTTP client | Axios with interceptors | Cleanest pattern for auto-attaching Bearer token and handling 401 → token refresh → retry |
| Real-time | Native WebSocket + custom hook | No extra dependency; aligns directly with FastAPI `ws/notifications` endpoint |
| Toast | Sonner | Lightweight, stacks correctly, works with Server Components |
| Data viz | Recharts + Tremor | Recharts for custom grade/attendance charts; Tremor for admin metric cards |
| Forms | React Hook Form + Zod | Zod schemas mirror Pydantic schemas — prevents invalid payloads from reaching the API |
| Search | cmdk | Powers `Cmd+K` command palette pattern for quick student/subject navigation |
| Table | TanStack Table v8 | Virtualized, sortable, filterable without re-implementing pagination |
| Token storage | Access token: memory (Zustand); Refresh token: HttpOnly cookie | Matches SECURITY.md recommendation; prevents XSS token theft |

---

## Full Technology Stack

### Core

| Package | Version | Purpose |
|---------|---------|---------|
| `next` | `^15.3` | App Router, Server Components, image optimization |
| `react` | `^19.0` | UI runtime |
| `react-dom` | `^19.0` | DOM renderer |
| `typescript` | `^5.4` | Type safety |

### Styling & Design System

| Package | Version | Purpose |
|---------|---------|---------|
| `tailwindcss` | `^3.4` | Utility-first CSS |
| `@shadcn/ui` | `latest CLI` | Unstyled, accessible component set (owned in-repo) |
| `@radix-ui/react-*` | `^1.x` | Primitive headless components underlying Shadcn |
| `framer-motion` | `^11.x` | Animations — score reveal, sidebar transitions, notification slide |
| `lucide-react` | `^0.400` | Icon set aligned with Shadcn defaults |
| `clsx` | `^2.x` | Conditional class names |
| `tailwind-merge` | `^2.x` | Merges conflicting Tailwind classes safely |
| `next-themes` | `^0.3` | Dark / light mode without flash |

### State Management

| Package | Version | Purpose |
|---------|---------|---------|
| `@tanstack/react-query` | `^5.40` | Server state — fetching, caching, background sync |
| `@tanstack/react-query-devtools` | `^5.40` | Dev-only query inspector |
| `zustand` | `^4.5` | Client state — auth session, sidebar, theme |
| `immer` | `^10.x` | Immutable state updates helper for complex Zustand slices |

### HTTP & Real-time

| Package | Version | Purpose |
|---------|---------|---------|
| `axios` | `^1.7` | HTTP client with interceptor chain |
| `axios-retry` | `^4.x` | Automatic retry on 503 (Render cold start) |

### Forms & Validation

| Package | Version | Purpose |
|---------|---------|---------|
| `react-hook-form` | `^7.52` | Performant, uncontrolled form management |
| `zod` | `^3.23` | Schema validation — mirrors Pydantic contracts |
| `@hookform/resolvers` | `^3.x` | Zod resolver bridge to React Hook Form |

### Data Visualization

| Package | Version | Purpose |
|---------|---------|---------|
| `recharts` | `^2.12` | Grade trend lines, attendance bar charts |
| `@tremor/react` | `^3.18` | Admin metric cards, area charts, donut charts |

### Tables & Search

| Package | Version | Purpose |
|---------|---------|---------|
| `@tanstack/react-table` | `^8.17` | Headless, sortable, paginated table engine |
| `cmdk` | `^1.0` | Command palette — `Cmd+K` global search |

### Notifications

| Package | Version | Purpose |
|---------|---------|---------|
| `sonner` | `^1.5` | Toast notifications — AI grade completion alerts |

### Dev Tooling

| Package | Version | Purpose |
|---------|---------|---------|
| `eslint` | `^8.x` | Linting |
| `eslint-config-next` | `^15.x` | Next.js rules preset |
| `prettier` | `^3.x` | Code formatting |
| `husky` | `^9.x` | Pre-commit hooks |

---

## Steps

### Step 8.1 — Bootstrap Next.js 15 Project

```bash
cd /workspaces/FinalYear_Projec

npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-turbopack

cd frontend
```

Expected output:
```
✔ Would you like to use TypeScript? Yes
✔ Would you like to use ESLint? Yes
✔ Would you like to use Tailwind CSS? Yes
✔ Would you like your code inside a `src/` directory? Yes
✔ Would you like to use App Router? Yes
✔ Would you like to use Turbopack? No
✔ Would you like to customize the import alias? Yes (@/*)
Creating a new Next.js app in .../frontend.
...
Success! Created frontend
```

---

### Step 8.2 — Install All Dependencies

```bash
cd /workspaces/FinalYear_Projec/frontend

# State, HTTP, forms
npm install @tanstack/react-query@^5.40.0 @tanstack/react-query-devtools@^5.40.0 \
  zustand@^4.5.0 immer@^10.0.0 \
  axios@^1.7.0 axios-retry@^4.0.0 \
  react-hook-form@^7.52.0 zod@^3.23.0 @hookform/resolvers@^3.0.0

# UI
npm install framer-motion@^11.0.0 lucide-react@^0.400.0 \
  next-themes@^0.3.0 clsx@^2.0.0 tailwind-merge@^2.0.0 \
  sonner@^1.5.0

# Charts, tables, search
npm install recharts@^2.12.0 @tremor/react@^3.18.0 \
  @tanstack/react-table@^8.17.0 cmdk@^1.0.0

# Shadcn/UI init (interactive — accept all defaults, use slate as base color)
npx shadcn@latest init
```

After Shadcn init, add these components:

```bash
npx shadcn@latest add button input label card badge \
  dialog sheet dropdown-menu avatar separator \
  table skeleton tabs toast progress
```

Expected output:
```
✔ Installing dependencies...
✔ Created tailwind.config.ts
✔ Created components.json
✔ Initialized project.
```

---

### Step 8.3 — Environment Configuration

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=https://lms-api-ukhs.onrender.com/api/v1
NEXT_PUBLIC_WS_URL=wss://lms-api-ukhs.onrender.com/api/v1/ws/notifications
```

Create `frontend/.env.local.example` (committed to git):

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws/notifications
```

> `.env.local` is gitignored. `.env.local.example` is committed.

---

### Step 8.4 — Axios API Client with JWT Auto-Attach and 401 Refresh

Create `src/lib/api/client.ts`:

```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import axiosRetry from "axios-retry";
import { useAuthStore } from "@/stores/authStore";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Retry on 503 (Render cold-start) — 3 attempts, exponential backoff
axiosRetry(apiClient, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (err) => err.response?.status === 503,
});

// Attach Bearer token on every request
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 → refresh → retry once
let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

apiClient.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (err.response?.status !== 401 || original._retry) {
      return Promise.reject(err);
    }

    original._retry = true;

    if (isRefreshing) {
      return new Promise((resolve) => {
        refreshQueue.push((token: string) => {
          original.headers.Authorization = `Bearer ${token}`;
          resolve(apiClient(original));
        });
      });
    }

    isRefreshing = true;

    try {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (!refreshToken) throw new Error("No refresh token");

      const { data } = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
        { refresh_token: refreshToken }
      );

      const { access_token, refresh_token: newRefresh } = data;
      useAuthStore.getState().setTokens(access_token, newRefresh);

      refreshQueue.forEach((cb) => cb(access_token));
      refreshQueue = [];

      original.headers.Authorization = `Bearer ${access_token}`;
      return apiClient(original);
    } catch {
      useAuthStore.getState().clearSession();
      if (typeof window !== "undefined") window.location.href = "/login";
      return Promise.reject(err);
    } finally {
      isRefreshing = false;
    }
  }
);
```

---

### Step 8.5 — Zustand Stores

Create `src/stores/authStore.ts`:

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthUser {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "admin" | "staff" | "student";
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: AuthUser) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),

      setUser: (user) => set({ user }),

      clearSession: () =>
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
    }),
    {
      name: "lms-auth",
      // Only persist refresh token — access token is rebuilt on mount via refresh
      partialize: (state) => ({
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
);
```

Create `src/stores/uiStore.ts`:

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  sidebarOpen: boolean;
  theme: "light" | "dark" | "system";
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTheme: (theme: "light" | "dark" | "system") => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: "system",
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setTheme: (theme) => set({ theme }),
    }),
    { name: "lms-ui" }
  )
);
```

---

### Step 8.6 — TanStack Query Key Factory

Create `src/lib/query/keys.ts`:

```typescript
export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  users: {
    all: () => ["users"] as const,
    detail: (id: string) => ["users", id] as const,
  },
  students: {
    all: () => ["students"] as const,
    detail: (id: string) => ["students", id] as const,
    me: () => ["students", "me"] as const,
    analytics: (id: string) => ["students", id, "analytics"] as const,
  },
  staff: {
    all: () => ["staff"] as const,
    detail: (id: string) => ["staff", id] as const,
    analytics: (id: string) => ["staff", id, "analytics"] as const,
  },
  academic: {
    departments: () => ["academic", "departments"] as const,
    classrooms: () => ["academic", "classrooms"] as const,
    subjects: () => ["academic", "subjects"] as const,
    sessionYears: () => ["academic", "session-years"] as const,
  },
  assignments: {
    all: () => ["assignments"] as const,
    detail: (id: string) => ["assignments", id] as const,
    submission: (id: string) => ["assignments", "submissions", id] as const,
  },
  quizzes: {
    all: () => ["quizzes"] as const,
    detail: (id: string) => ["quizzes", id] as const,
    attempt: (id: string) => ["quizzes", "attempts", id] as const,
  },
  attendance: {
    summary: (studentId: string) => ["attendance", studentId, "summary"] as const,
  },
  notifications: {
    mine: () => ["notifications", "me"] as const,
  },
  leave: {
    pending: () => ["leave", "pending"] as const,
    detail: (id: string) => ["leave", id] as const,
  },
  analytics: {
    classroom: (id: string) => ["analytics", "classrooms", id] as const,
  },
} as const;
```

---

### Step 8.7 — WebSocket Notification Hook (The "Real-time Bridge")

Create `src/lib/hooks/useNotificationStream.ts`:

```typescript
"use client";

import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/authStore";
import { queryKeys } from "@/lib/query/keys";

// Event shape pushed by Celery grading tasks via manager.send_to_user()
interface WSEvent {
  type:
    | "submission:graded"
    | "attempt:graded"
    | "notification:new"
    | "item:update";
  payload: Record<string, unknown>;
}

export function useNotificationStream(): void {
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      if (event.data === "pong") return;

      let msg: WSEvent;
      try {
        msg = JSON.parse(event.data) as WSEvent;
      } catch {
        return;
      }

      switch (msg.type) {
        case "submission:graded": {
          const { submission_id, assignment_id, score, ai_feedback } =
            msg.payload as {
              submission_id: string;
              assignment_id: string;
              score: number;
              ai_feedback: string;
            };

          // Invalidate so TanStack Query re-fetches with new score
          queryClient.invalidateQueries({
            queryKey: queryKeys.assignments.submission(submission_id),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.assignments.detail(assignment_id),
          });

          toast.success(`Assignment graded! Score: ${score.toFixed(1)}`, {
            description: ai_feedback?.slice(0, 120),
            duration: 8000,
          });
          break;
        }

        case "attempt:graded": {
          const { attempt_id, quiz_id, score } = msg.payload as {
            attempt_id: string;
            quiz_id: string;
            score: number;
          };

          queryClient.invalidateQueries({
            queryKey: queryKeys.quizzes.attempt(attempt_id),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.quizzes.detail(quiz_id),
          });

          toast.success(`Quiz graded! Score: ${score.toFixed(1)}`, {
            duration: 6000,
          });
          break;
        }

        case "notification:new": {
          // Refresh notification badge
          queryClient.invalidateQueries({
            queryKey: queryKeys.notifications.mine(),
          });
          break;
        }

        case "item:update": {
          // Generic invalidation for broadcast updates
          queryClient.invalidateQueries();
          break;
        }
      }
    },
    [queryClient]
  );

  useEffect(() => {
    if (!accessToken) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}?token=${accessToken}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = handleMessage;

    ws.onopen = () => {
      // Render LB idle timeout = 30s — ping every 25s to keep connection alive
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, 25_000);
    };

    ws.onclose = () => {
      if (pingRef.current) clearInterval(pingRef.current);
    };

    ws.onerror = () => {
      ws.close();
    };

    return () => {
      if (pingRef.current) clearInterval(pingRef.current);
      ws.close();
    };
  }, [accessToken, handleMessage]);
}
```

---

### Step 8.8 — AI Grade Status Component with Framer Motion

Create `src/components/grades/AIGradeStatus.tsx`:

```typescript
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, Clock } from "lucide-react";

interface Props {
  status: "pending" | "graded" | "not_submitted";
  score?: number | null;
  maxScore?: number;
  aiFeedback?: string | null;
}

export function AIGradeStatus({ status, score, maxScore = 100, aiFeedback }: Props) {
  return (
    <div className="space-y-3">
      {/* Status badge */}
      {status === "pending" && (
        <Badge variant="secondary" className="gap-1.5">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          AI grading in progress...
        </Badge>
      )}

      {status === "not_submitted" && (
        <Badge variant="outline" className="gap-1.5 text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          Not submitted
        </Badge>
      )}

      {/* Score reveal — slides in when graded */}
      <AnimatePresence>
        {status === "graded" && score != null && (
          <motion.div
            key="score"
            initial={{ opacity: 0, y: 16, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 24 }}
            className="rounded-lg border bg-card p-4 shadow-sm"
          >
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <span className="font-semibold text-lg">
                {score.toFixed(1)}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  / {maxScore}
                </span>
              </span>
              <Badge variant="default" className="ml-auto">
                AI Graded
              </Badge>
            </div>

            {aiFeedback && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-sm text-muted-foreground leading-relaxed"
              >
                {aiFeedback}
              </motion.p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

---

### Step 8.9 — Auth Guard (Route Protection)

Create `src/components/auth/AuthGuard.tsx`:

```typescript
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";

type Role = "admin" | "staff" | "student";

interface Props {
  children: React.ReactNode;
  allowedRoles?: Role[];
}

export function AuthGuard({ children, allowedRoles }: Props) {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }

    if (allowedRoles && user && !allowedRoles.includes(user.role as Role)) {
      // Redirect to the correct role dashboard instead of a bare 403
      router.replace(`/${user.role}`);
    }
  }, [isAuthenticated, user, allowedRoles, router]);

  if (!isAuthenticated) return null;
  if (allowedRoles && user && !allowedRoles.includes(user.role as Role)) return null;

  return <>{children}</>;
}
```

---

### Step 8.10 — Zod Validation Schemas (Frontend Contract)

Create `src/lib/schemas/auth.schema.ts`:

```typescript
import { z } from "zod";

// Mirrors POST /auth/token (OAuth2PasswordRequestForm)
export const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
```

Create `src/lib/schemas/assignment.schema.ts`:

```typescript
import { z } from "zod";

// IMPORTANT: Backend datetime fields are UTC naive — no "Z" suffix.
// Zod coerce.date() parses ISO strings. The API layer must call .toISOString()
// and strip the trailing "Z" when building request bodies.
export const assignmentCreateSchema = z.object({
  title: z.string().min(1).max(255),
  description: z.string().optional(),
  subject_id: z.string().uuid("Invalid subject ID"),
  staff_id: z.string().uuid("Invalid staff ID"),
  due_date: z.coerce.date().optional(),
  max_score: z.number().min(0).max(1000).default(100),
  ai_grading_enabled: z.boolean().default(false),
});

export type AssignmentCreateValues = z.infer<typeof assignmentCreateSchema>;
```

Create `src/lib/schemas/quiz.schema.ts`:

```typescript
import { z } from "zod";

export const quizCreateSchema = z.object({
  title: z.string().min(1).max(255),
  description: z.string().optional(),
  subject_id: z.string().uuid(),
  staff_id: z.string().uuid(),
  time_limit_minutes: z.number().int().positive().optional(),
  max_attempts: z.number().int().min(1).default(1),
  pass_score: z.number().min(0).max(100).default(50),
  due_date: z.coerce.date().optional(),
  ai_grading_enabled: z.boolean().default(false),
});

export type QuizCreateValues = z.infer<typeof quizCreateSchema>;

export const questionCreateSchema = z.object({
  text: z.string().min(1),
  question_type: z.enum(["multiple_choice", "true_false", "essay"]),
  option_a: z.string().optional(),
  option_b: z.string().optional(),
  option_c: z.string().optional(),
  option_d: z.string().optional(),
  correct_answer: z.string().optional(),
  points: z.number().min(0).default(1),
});
```

---

### Step 8.11 — TypeScript API Types

Create `src/types/models.ts`:

```typescript
// Mirrors all Pydantic Response schemas from the FastAPI backend.
// UUID fields are strings in JSON. Datetime fields are ISO strings without TZ suffix.

export interface BaseResponse {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface UserResponse extends BaseResponse {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "admin" | "staff" | "student";
  is_active: boolean;
  last_login: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface StudentProfileResponse extends BaseResponse {
  user_id: string;
  classroom_id: string | null;
  session_year_id: string | null;
  roll_number: string | null;
  date_of_birth: string | null;
  address: string | null;
  phone_number: string | null;
  profile_picture: string | null;
}

export interface StaffProfileResponse extends BaseResponse {
  user_id: string;
  department_id: string | null;
  designation: string | null;
  phone_number: string | null;
  profile_picture: string | null;
}

export interface AssignmentResponse extends BaseResponse {
  title: string;
  description: string | null;
  subject_id: string;
  staff_id: string;
  status: "draft" | "published" | "closed";
  due_date: string | null;
  max_score: number;
  file_url: string | null;
  ai_grading_enabled: boolean;
}

export interface SubmissionResponse extends BaseResponse {
  assignment_id: string;
  student_id: string;
  status: "pending" | "submitted" | "graded";
  file_url: string | null;
  score: number | null;
  feedback: string | null;
  submitted_at: string | null;
  graded_at: string | null;
  ai_feedback: string | null;
}

export interface QuizResponse extends BaseResponse {
  title: string;
  description: string | null;
  subject_id: string;
  staff_id: string;
  status: "draft" | "published" | "closed";
  time_limit_minutes: number | null;
  max_attempts: number;
  pass_score: number;
  due_date: string | null;
  ai_grading_enabled: boolean;
}

export interface QuizAttemptResponse extends BaseResponse {
  quiz_id: string;
  student_id: string;
  status: "in_progress" | "submitted" | "graded";
  score: number | null;
  started_at: string | null;
  submitted_at: string | null;
}

export interface NotificationResponse extends BaseResponse {
  sender_id: string | null;
  recipient_id: string;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  read_at: string | null;
}

export interface LeaveRequestResponse extends BaseResponse {
  user_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  reviewed_by_id: string | null;
  rejection_reason: string | null;
}

export interface DepartmentResponse extends BaseResponse {
  name: string;
  description: string | null;
}

export interface ClassRoomResponse extends BaseResponse {
  name: string;
  department_id: string;
  session_year_id: string;
}

export interface SubjectResponse extends BaseResponse {
  name: string;
  code: string;
  classroom_id: string;
  staff_id: string | null;
}

// Pagination envelope
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// Standard API error envelope
export interface APIError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}
```

---

### Step 8.12 — Dashboard Shell Layout

Create `src/app/(dashboard)/layout.tsx`:

```typescript
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Toaster } from "sonner";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useAuthStore } from "@/stores/authStore";
import { useNotificationStream } from "@/lib/hooks/useNotificationStream";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { useUIStore } from "@/stores/uiStore";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,   // 2 minutes
      gcTime: 1000 * 60 * 10,     // 10 minutes
      retry: 2,
    },
  },
});

function DashboardInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);

  // Initialize WebSocket notification stream
  useNotificationStream();

  useEffect(() => {
    if (!isAuthenticated) router.replace("/login");
  }, [isAuthenticated, router]);

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div
        className={`flex flex-col flex-1 overflow-hidden transition-all duration-200 ${
          sidebarOpen ? "ml-64" : "ml-16"
        }`}
      >
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
      <Toaster position="bottom-right" richColors closeButton />
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardInner>{children}</DashboardInner>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

---

### Step 8.13 — Role-Aware Sidebar

Create `src/components/layout/Sidebar.tsx`:

```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, GraduationCap, BookOpen,
  ClipboardCheck, Bell, LogOut, ChevronLeft, BarChart3,
  FileText, Calendar, Briefcase,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { Button } from "@/components/ui/button";

const adminNav = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/students", label: "Students", icon: GraduationCap },
  { href: "/admin/staff", label: "Staff", icon: Briefcase },
  { href: "/admin/academic", label: "Academic", icon: BookOpen },
  { href: "/admin/analytics", label: "Analytics", icon: BarChart3 },
];

const staffNav = [
  { href: "/staff", label: "Overview", icon: LayoutDashboard },
  { href: "/staff/assignments", label: "Assignments", icon: FileText },
  { href: "/staff/quizzes", label: "Quizzes", icon: ClipboardCheck },
  { href: "/staff/attendance", label: "Attendance", icon: Calendar },
  { href: "/staff/leave", label: "Leave", icon: Calendar },
];

const studentNav = [
  { href: "/student", label: "Overview", icon: LayoutDashboard },
  { href: "/student/assignments", label: "Assignments", icon: FileText },
  { href: "/student/quizzes", label: "Quizzes", icon: ClipboardCheck },
  { href: "/student/attendance", label: "Attendance", icon: Calendar },
  { href: "/student/leave", label: "Leave", icon: Calendar },
];

const navMap = { admin: adminNav, staff: staffNav, student: studentNav };

export function Sidebar() {
  const pathname = usePathname();
  const { user, clearSession } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const nav = navMap[user?.role ?? "student"];

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-full bg-card border-r flex flex-col transition-all duration-200 z-50",
        sidebarOpen ? "w-64" : "w-16"
      )}
    >
      {/* Logo + collapse button */}
      <div className="flex items-center justify-between p-4 border-b">
        {sidebarOpen && (
          <span className="font-bold text-lg tracking-tight">SchoolLMS</span>
        )}
        <Button variant="ghost" size="icon" onClick={toggleSidebar}>
          <ChevronLeft
            className={cn("h-4 w-4 transition-transform", !sidebarOpen && "rotate-180")}
          />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
              pathname === href || pathname.startsWith(href + "/")
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {sidebarOpen && <span>{label}</span>}
          </Link>
        ))}
      </nav>

      {/* User + Logout */}
      <div className="p-4 border-t">
        {sidebarOpen && user && (
          <p className="text-xs text-muted-foreground mb-2 truncate">
            {user.first_name} {user.last_name}
          </p>
        )}
        <Button
          variant="ghost"
          size={sidebarOpen ? "sm" : "icon"}
          className="w-full justify-start gap-2 text-destructive hover:bg-destructive/10"
          onClick={clearSession}
        >
          <LogOut className="h-4 w-4" />
          {sidebarOpen && "Sign out"}
        </Button>
      </div>
    </aside>
  );
}
```

---

## The Async Handshake — Full Flow Specification

This is the end-to-end contract for AI grading. Every step maps to a specific component,
hook, or API call.

```
1. [Student UI]        User opens /student/assignments/{id}
                       → Page mounts → useQuery(queryKeys.assignments.detail(id))
                       → Fetches AssignmentResponse (ai_grading_enabled=true)

2. [Student UI]        User clicks "Submit Assignment"
                       → SubmissionUpload.tsx calls POST /assignments/{id}/submit
                       → useMutation with onSuccess → stores submission_id in state
                       → Status = "submitted" → AIGradeStatus renders pending badge

3. [Celery Worker]     grade_submission_task picks up job from Redis queue
                       → Calls grade_essay_scored() via OpenRouter
                       → Writes score + ai_feedback to AssignmentSubmission row
                       → Calls manager.send_to_user(student_id, {
                             type: "submission:graded",
                             payload: { submission_id, assignment_id, score, ai_feedback }
                           })

4. [WebSocket Hook]    useNotificationStream.handleMessage receives event
                       → Matches type "submission:graded"
                       → queryClient.invalidateQueries(["assignments","submissions",submission_id])
                       → TanStack Query re-fetches SubmissionResponse
                       → New score is now in cache

5. [Student UI]        AIGradeStatus re-renders with status="graded", score=88.5
                       → AnimatePresence triggers Framer Motion spring animation
                       → Score slides in from below with spring(300, 24)
                       → toast.success("Assignment graded! Score: 88.5") fired by hook

Total perceived latency: 1–3 s typical (OpenRouter response time dominates)
```

---

## Role-Based Dashboard Specifications

### Admin Dashboard (`/admin`)

| Widget | Data Source | Component |
|--------|-------------|-----------|
| Total users by role | `GET /api/v1/admin/users` (aggregated client-side) | Tremor `DonutChart` |
| Students enrolled | `GET /api/v1/students` (total count) | Tremor `Metric` |
| Departments | `GET /api/v1/academic/departments` | Tremor `List` |
| Assignment completion rate | `GET /api/v1/analytics/classrooms/{id}` | Recharts `BarChart` |
| Grade distribution | Analytics endpoint | Recharts `AreaChart` |
| User management table | `GET /api/v1/admin/users` | `DataTable` with TanStack Table |
| Pending leave requests | `GET /api/v1/leave/pending` | Shadcn `Badge` list |

### Staff Dashboard (`/staff`)

| Widget | Data Source | Component |
|--------|-------------|-----------|
| My assignments | `GET /api/v1/assignments` | Card grid |
| Pending AI grading | Submission list filtered by `status=submitted` | `AIGradeStatus` list |
| Class attendance | `GET /api/v1/attendance/students/{id}/summary` | Recharts `PieChart` |
| Staff analytics | `GET /api/v1/analytics/staff/{id}` | Tremor `BarList` |
| Leave reviews | `GET /api/v1/leave/pending` | Review table with approve/reject |

### Student Dashboard (`/student`)

| Widget | Data Source | Component |
|--------|-------------|-----------|
| Grade snapshot | All submissions for this student | `GradeCard` per subject |
| Pending assignments | Assignment list filtered by due_date | Deadline badge |
| Attendance % | `GET /api/v1/attendance/students/{id}/summary` | Recharts `RadialBar` |
| Recent notifications | `GET /api/v1/notifications/me` | Notification list |
| Quiz attempts | `GET /api/v1/quizzes` | Available quiz cards |
| AI grade status | `GET /api/v1/assignments/submissions/{id}` | `AIGradeStatus` |

---

## Acceptance Criteria

All items must be true before Phase 8 is considered complete.

- [ ] `npm run build` in `frontend/` exits with code 0 and no TypeScript errors
- [ ] `npm run lint` exits with code 0
- [ ] `POST /auth/token` happy-path: access + refresh tokens written to Zustand store
- [ ] `GET /auth/me` called on mount; `UserResponse` parsed and stored; role claim readable
- [ ] Navigating to `/admin` as `role=student` redirects to `/student`
- [ ] Navigating to any `/dashboard/*` route without a token redirects to `/login`
- [ ] 401 response on any API call triggers refresh → retry transparently (no visible error)
- [ ] WebSocket connects within 3 s of login on a production deployment
- [ ] `"ping"` sent every 25 s; `"pong"` received and not rendered to user
- [ ] `submission:graded` WS event triggers `invalidateQueries` + Sonner toast
- [ ] `AIGradeStatus` renders pending badge immediately after submit; score slides in after WS event
- [ ] Framer Motion score reveal animation completes in ≤ 400 ms
- [ ] Login form with blank username shows Zod error "Username is required"
- [ ] Assignment create form with `due_date` sends datetime without trailing "Z" to API
- [ ] `Cmd+K` opens command palette; typing a name filters visible suggestions

---

## Rollback

If Phase 8 introduces regressions:

1. The frontend lives entirely in `frontend/` — it does not modify any `backend/` files.
2. To roll back: `rm -rf frontend/` and restore from `git checkout HEAD -- frontend/`.
3. The backend is fully unaffected by frontend removal.
4. If dependency conflicts arise: `rm -rf frontend/node_modules frontend/.next && npm install`.

---

## Pre-conditions Before Executing This Plan

1. Phase 7 (production hardening) is complete and the Render deployment is healthy.
2. `GET https://lms-api-ukhs.onrender.com/api/v1/health` returns `{"status": "ok"}`.
3. Node.js `>=20` and `npm >=10` are available in the dev environment.
4. `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` are known (values provided above).
5. The executing agent has write access to `frontend/` in the workspace root.

---

*ExecPlan authored: 2026-04-26 | Phase 8 | Author: GitHub Copilot*
