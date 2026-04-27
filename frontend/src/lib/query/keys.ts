/**
 * Centralised TanStack Query key factory.
 * All keys are typed tuples so refactoring a segment propagates everywhere.
 */
export const queryKeys = {
  // ── Auth ────────────────────────────────────────────────────────────────
  auth: {
    me: () => ["auth", "me"] as const,
  },

  // ── Users ───────────────────────────────────────────────────────────────
  users: {
    all: (params?: Record<string, unknown>) =>
      ["users", "list", params ?? {}] as const,
    detail: (id: string) => ["users", "detail", id] as const,
  },

  // ── Students ────────────────────────────────────────────────────────────
  students: {
    all: (params?: Record<string, unknown>) =>
      ["students", "list", params ?? {}] as const,
    detail: (id: string) => ["students", "detail", id] as const,
    me: () => ["students", "me"] as const,
    analytics: (id: string) => ["students", "analytics", id] as const,
  },

  // ── Staff ───────────────────────────────────────────────────────────────
  staff: {
    all: (params?: Record<string, unknown>) =>
      ["staff", "list", params ?? {}] as const,
    detail: (id: string) => ["staff", "detail", id] as const,
    analytics: (id: string) => ["staff", "analytics", id] as const,
  },

  // ── Academic ────────────────────────────────────────────────────────────
  academic: {
    departments: () => ["academic", "departments"] as const,
    classrooms: (params?: Record<string, unknown>) =>
      ["academic", "classrooms", params ?? {}] as const,
    subjects: (params?: Record<string, unknown>) =>
      ["academic", "subjects", params ?? {}] as const,
    sessionYears: () => ["academic", "session-years"] as const,
  },

  // ── Assignments ─────────────────────────────────────────────────────────
  assignments: {
    all: (params?: Record<string, unknown>) =>
      ["assignments", "list", params ?? {}] as const,
    detail: (id: string) => ["assignments", "detail", id] as const,
    submissions: (assignmentId: string) =>
      ["assignments", "submissions", assignmentId] as const,
    submission: (submissionId: string) =>
      ["assignments", "submission", submissionId] as const,
  },

  // ── Assessments (Quizzes) ───────────────────────────────────────────────
  quizzes: {
    all: (params?: Record<string, unknown>) =>
      ["quizzes", "list", params ?? {}] as const,
    detail: (id: string) => ["quizzes", "detail", id] as const,
    attempt: (attemptId: string) => ["quizzes", "attempt", attemptId] as const,
    myAttempts: () => ["quizzes", "my-attempts"] as const,
  },

  // ── Attendance ──────────────────────────────────────────────────────────
  attendance: {
    summary: (params?: Record<string, unknown>) =>
      ["attendance", "summary", params ?? {}] as const,
    records: (params?: Record<string, unknown>) =>
      ["attendance", "records", params ?? {}] as const,
  },

  // ── Notifications ────────────────────────────────────────────────────────
  notifications: {
    mine: (params?: Record<string, unknown>) =>
      ["notifications", "mine", params ?? {}] as const,
  },

  // ── Leave ────────────────────────────────────────────────────────────────
  leave: {
    pending: () => ["leave", "pending"] as const,
    all: (params?: Record<string, unknown>) =>
      ["leave", "list", params ?? {}] as const,
    detail: (id: string) => ["leave", "detail", id] as const,
  },

  // ── Analytics ────────────────────────────────────────────────────────────
  analytics: {
    classroom: (classroomId: string) =>
      ["analytics", "classroom", classroomId] as const,
    platform: () => ["analytics", "platform"] as const,
  },
} as const;
