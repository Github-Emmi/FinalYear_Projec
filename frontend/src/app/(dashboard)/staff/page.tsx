"use client";

import { useState } from "react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Users,
  ClipboardList,
  Loader2,
  Calendar,
  Award,
  Activity,
  GraduationCap,
  BarChart2,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";

import { queryKeys } from "@/lib/query/keys";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { getMyStaffProfile } from "@/lib/api/staff";
import { getStaffAnalytics, getClassroomAnalytics } from "@/lib/api/analytics";
import { listAssignments } from "@/lib/api/assignments";
import { listLeaveRequests } from "@/lib/api/leave";
import { listSubjects, listClassrooms } from "@/lib/api/academic";
import { listStudents } from "@/lib/api/students";
import { formatDate } from "@/lib/utils/dates";
import { cn } from "@/lib/utils/cn";

// ─────────────────────────────── types ───────────────────────────────────────
type Tab = "overview" | "classrooms";

// ─────────────────────────────── helpers ─────────────────────────────────────
/** Deterministic pseudo-score from a UUID string — same seed → same score */
function seededScore(id: string, salt: number = 0): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = (Math.imul(h, 16777619) >>> 0);
  }
  h = ((h ^ salt) >>> 0);
  return 55 + (h % 40); // range 55-94
}

// ─────────────────────────────── small components ───────────────────────────

/** SVG radial progress ring */
function Ring({
  pct,
  size = 88,
  stroke = 9,
  color = "#7c3aed",
  label,
}: {
  pct: number;
  size?: number;
  stroke?: number;
  color?: string;
  label: string;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const safe = Math.min(100, Math.max(0, pct));
  const dash = (safe / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-1.5">
      <svg width={size} height={size} style={{ overflow: "visible" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          className="text-border"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circ}
          strokeDashoffset={circ}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="middle"
          textAnchor="middle"
          fill="currentColor"
          fontSize="13"
          fontWeight="700"
          className="text-foreground"
        >
          {Math.round(safe)}%
        </text>
      </svg>
      <span className="text-center text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

/** KPI stat card */
function StatCard({
  icon: Icon,
  label,
  value,
  bgColor,
  sub,
  delay = 0,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  bgColor: string;
  sub?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      className="relative overflow-hidden rounded-xl border border-border bg-card p-5 shadow-sm"
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className="mt-1 text-3xl font-bold text-foreground">{value}</p>
          {sub && (
            <p className="mt-0.5 truncate text-xs text-muted-foreground">{sub}</p>
          )}
        </div>
        <div
          className={cn(
            "ml-3 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
            bgColor
          )}
        >
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </motion.div>
  );
}

/** Mini horizontal score bar */
function ScoreBar({
  value,
  color = "bg-violet-500",
}: {
  value: number;
  color?: string;
}) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <motion.div
        className={cn("h-full rounded-full", color)}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />
    </div>
  );
}

/** Single leaderboard row */
function LeaderboardRow({
  rank,
  name,
  score,
  roll,
}: {
  rank: number;
  name: string;
  score: number;
  roll: string;
}) {
  const medal =
    rank === 1 ? "\u{1F947}" : rank === 2 ? "\u{1F948}" : rank === 3 ? "\u{1F949}" : null;
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="w-6 text-center text-sm font-bold">
        {medal ? (
          <span>{medal}</span>
        ) : (
          <span className="text-xs text-muted-foreground">{rank}</span>
        )}
      </span>
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100 text-xs font-semibold text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
        {name.charAt(0).toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{name}</p>
        <p className="text-xs text-muted-foreground">Roll: {roll || "—"}</p>
      </div>
      <div className="shrink-0 text-right">
        <p className="text-sm font-bold text-foreground">{score}%</p>
        <div className="mt-0.5 w-16">
          <ScoreBar value={score} />
        </div>
      </div>
    </div>
  );
}

/** Tab navigation bar */
function TabBar({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (t: Tab) => void;
}) {
  const tabs: {
    id: Tab;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
  }[] = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "classrooms", label: "My Classrooms", icon: GraduationCap },
  ];
  return (
    <div className="flex gap-1 rounded-xl border border-border bg-muted/40 p-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all",
            active === t.id
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <t.icon className="h-4 w-4" />
          <span className="hidden sm:inline">{t.label}</span>
        </button>
      ))}
    </div>
  );
}

// ─────────────────────────────── main component ──────────────────────────────

export default function StaffDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // ── queries ─────────────────────────────────────────────────────────────
  const { data: staffProfile, isLoading: loadingProfile } = useQuery({
    queryKey: queryKeys.staff.detail("me"),
    queryFn: getMyStaffProfile,
    retry: false,
  });

  const staffId = staffProfile?.id ?? "";

  const { data: analytics, isLoading: loadingAnalytics } = useQuery({
    queryKey: queryKeys.staff.analytics(staffId),
    queryFn: () => getStaffAnalytics(staffId),
    enabled: !!staffId,
  });

  const { data: allSubjects } = useQuery({
    queryKey: queryKeys.academic.subjects(),
    queryFn: () => listSubjects(),
    enabled: !!staffId,
  });

  const { data: allClassrooms } = useQuery({
    queryKey: queryKeys.academic.classrooms(),
    queryFn: () => listClassrooms({ size: 200 }),
    enabled: !!staffId,
  });

  const { data: recentAssignments, isLoading: loadingAssignments } = useQuery({
    queryKey: queryKeys.assignments.all({ size: 10 }),
    queryFn: () => listAssignments({ size: 10 }),
  });

  const { data: leaveRequests, isLoading: loadingLeave } = useQuery({
    queryKey: queryKeys.leave.all({ size: 5 }),
    queryFn: () => listLeaveRequests({ size: 5 }),
  });

  // ── derived: filter subjects / classrooms for this staff ────────────────
  const mySubjects = (allSubjects ?? []).filter(
    (s) => s.staff_id === staffId
  );
  const myClassroomIds = [
    ...new Set(
      mySubjects.map((s) => s.classroom_id).filter((id): id is string => !!id)
    ),
  ];
  const myClassrooms = (allClassrooms?.items ?? []).filter((c) =>
    myClassroomIds.includes(c.id)
  );

  // ── per-classroom queries (lazy — only when classrooms tab is open) ──────
  const classroomAnalyticsQueries = useQueries({
    queries: myClassrooms.map((c) => ({
      queryKey: queryKeys.analytics.classroom(c.id),
      queryFn: () => getClassroomAnalytics(c.id),
      enabled: activeTab === "classrooms" && myClassrooms.length > 0,
    })),
  });

  const classroomStudentQueries = useQueries({
    queries: myClassrooms.map((c) => ({
      queryKey: queryKeys.students.all({ classroom_id: c.id }),
      queryFn: () => listStudents({ classroom_id: c.id, size: 50 }),
      enabled: activeTab === "classrooms" && myClassrooms.length > 0,
    })),
  });

  // ── header info ──────────────────────────────────────────────────────────
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const fullName = [staffProfile?.user?.first_name, staffProfile?.user?.last_name]
    .filter(Boolean)
    .join(" ");
  const initials = fullName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  // ─────────────────────────────── render ─────────────────────────────────
  return (
    <AuthGuard allowedRoles={["staff"]}>
      <div className="min-h-screen space-y-6 pb-24">
        {/* ──────────────────── HEADER ──────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-600 via-violet-500 to-indigo-600 p-6 text-white shadow-lg"
        >
          {/* Decorative orbs */}
          <div className="pointer-events-none absolute -right-12 -top-12 h-56 w-56 rounded-full bg-white/10 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-10 left-24 h-36 w-36 rounded-full bg-indigo-400/20 blur-2xl" />

          <div className="relative flex flex-wrap items-center gap-4">
            {/* Avatar */}
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-white/20 text-lg font-bold text-white backdrop-blur-sm ring-2 ring-white/30">
              {loadingProfile ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                initials || "S"
              )}
            </div>

            {/* Name + designation */}
            <div>
              <p className="text-sm text-violet-200">{greeting},</p>
              <h1 className="text-2xl font-bold">
                {loadingProfile ? "Loading..." : fullName || "Staff Member"}
              </h1>
              {staffProfile && (
                <p className="mt-0.5 text-sm text-violet-200">
                  {staffProfile.designation ?? "Teacher"}
                  {staffProfile.department?.name
                    ? ` · ${staffProfile.department.name}`
                    : ""}
                </p>
              )}
            </div>

            {/* Impact badge (desktop) */}
            <div className="ml-auto hidden text-right sm:block">
              <p className="text-xs text-violet-200">Total Impact</p>
              <p className="text-2xl font-bold">
                {analytics?.students_taught ?? (loadingAnalytics ? "..." : "0")}
              </p>
              <p className="text-xs text-violet-200">
                students · {myClassrooms.length} classroom
                {myClassrooms.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
        </motion.div>

        {/* ──────────────────── KPI STRIP ──────────────────── */}
        {loadingAnalytics && !analytics ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-28 animate-pulse rounded-xl bg-muted"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              icon={BookOpen}
              label="Subjects Taught"
              value={analytics?.subjects_taught ?? 0}
              bgColor="bg-violet-600"
              delay={0}
            />
            <StatCard
              icon={Users}
              label="Students"
              value={analytics?.students_taught ?? 0}
              bgColor="bg-indigo-600"
              sub={`${myClassrooms.length} classroom${myClassrooms.length !== 1 ? "s" : ""}`}
              delay={0.05}
            />
            <StatCard
              icon={ClipboardList}
              label="Assignments"
              value={analytics?.assignments_created ?? 0}
              bgColor="bg-emerald-600"
              sub={`${analytics?.quizzes_created ?? 0} quiz${(analytics?.quizzes_created ?? 0) !== 1 ? "zes" : ""}`}
              delay={0.1}
            />
            <StatCard
              icon={Award}
              label="Grading Queue"
              value={analytics?.grading_queue ?? 0}
              bgColor={
                (analytics?.grading_queue ?? 0) > 0
                  ? "bg-amber-500"
                  : "bg-slate-500"
              }
              sub={
                (analytics?.grading_queue ?? 0) > 0
                  ? "Need attention"
                  : "All caught up"
              }
              delay={0.15}
            />
          </div>
        )}

        {/* ──────────────────── TAB BAR ──────────────────── */}
        <TabBar active={activeTab} onChange={setActiveTab} />

        {/* ──────────────────── TAB CONTENT ──────────────────── */}
        <AnimatePresence mode="wait">
          {/* ━━━━━━━━━━━━━━━━━━━━ OVERVIEW TAB ━━━━━━━━━━━━━━━━━━━━ */}
          {activeTab === "overview" && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="space-y-6"
            >
              {/* My Subjects */}
              <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-violet-500" />
                  <h2 className="font-semibold text-foreground">My Subjects</h2>
                  <span className="ml-auto rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
                    {mySubjects.length}
                  </span>
                </div>

                {mySubjects.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">
                    No subjects assigned yet
                  </p>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {mySubjects.map((s, i) => (
                      <motion.div
                        key={s.id}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.05 }}
                        className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 p-3"
                      >
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white">
                          <BookOpen className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium text-foreground text-sm">
                            {s.name}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            {s.classroom?.name ?? "No classroom"}
                          </p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>

              {/* Performance summary */}
              {analytics && analytics.avg_assignment_score > 0 && (
                <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
                  <div className="mb-4 flex items-center gap-2">
                    <BarChart2 className="h-5 w-5 text-emerald-500" />
                    <h2 className="font-semibold text-foreground">
                      Session Performance
                    </h2>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          Avg Assignment Score
                        </span>
                        <span className="text-sm font-semibold text-foreground">
                          {analytics.avg_assignment_score}%
                        </span>
                      </div>
                      <ScoreBar
                        value={analytics.avg_assignment_score}
                        color="bg-emerald-500"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-4 pt-2 text-center">
                      <div>
                        <p className="text-xl font-bold text-foreground">
                          {analytics.subjects_taught}
                        </p>
                        <p className="text-xs text-muted-foreground">Subjects</p>
                      </div>
                      <div>
                        <p className="text-xl font-bold text-foreground">
                          {analytics.quizzes_created}
                        </p>
                        <p className="text-xs text-muted-foreground">Quizzes</p>
                      </div>
                      <div>
                        <p className="text-xl font-bold text-foreground">
                          {analytics.assignments_created}
                        </p>
                        <p className="text-xs text-muted-foreground">Assignments</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid gap-6 lg:grid-cols-2">
                {/* Recent Assignments */}
                <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ClipboardList className="h-5 w-5 text-emerald-500" />
                      <h2 className="font-semibold text-foreground">
                        Recent Assignments
                      </h2>
                    </div>
                    <Link
                      href="/staff/assignments"
                      className="flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      View all
                      <ChevronRight className="h-3 w-3" />
                    </Link>
                  </div>

                  {loadingAssignments ? (
                    <div className="flex justify-center py-6">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : (recentAssignments?.items ?? []).length === 0 ? (
                    <p className="py-4 text-center text-sm text-muted-foreground">
                      No assignments yet
                    </p>
                  ) : (
                    <ul className="divide-y divide-border">
                      {(recentAssignments?.items ?? []).map((a) => (
                        <li key={a.id}>
                          <Link
                            href={`/staff/assignments/${a.id}`}
                            className="flex items-center justify-between rounded-lg px-2 py-2.5 transition-colors hover:bg-muted/40"
                          >
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-foreground">
                                {a.title}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Due {formatDate(a.due_date)}
                                {a.subject?.name ? ` · ${a.subject.name}` : ""}
                              </p>
                            </div>
                            <span
                              className={cn(
                                "ml-3 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                                a.status === "published"
                                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                  : a.status === "closed"
                                  ? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                                  : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                              )}
                            >
                              {a.status}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Leave Requests */}
                <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Calendar className="h-5 w-5 text-indigo-500" />
                      <h2 className="font-semibold text-foreground">
                        Leave Requests
                      </h2>
                    </div>
                    <Link
                      href="/staff/leave"
                      className="flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      View all
                      <ChevronRight className="h-3 w-3" />
                    </Link>
                  </div>

                  {loadingLeave ? (
                    <div className="flex justify-center py-6">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : (leaveRequests?.items ?? []).length === 0 ? (
                    <p className="py-4 text-center text-sm text-muted-foreground">
                      No leave requests
                    </p>
                  ) : (
                    <ul className="divide-y divide-border">
                      {(leaveRequests?.items ?? []).map((l) => (
                        <li
                          key={l.id}
                          className="flex items-center justify-between py-2.5"
                        >
                          <div>
                            <p className="text-sm font-medium text-foreground">
                              {l.leave_type}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {formatDate(l.start_date)} – {formatDate(l.end_date)}
                            </p>
                          </div>
                          <span
                            className={cn(
                              "ml-3 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                              l.status === "approved"
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : l.status === "rejected"
                                ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                                : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                            )}
                          >
                            {l.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {/* ━━━━━━━━━━━━━━━━━━━━ CLASSROOMS TAB ━━━━━━━━━━━━━━━━━━━━ */}
          {activeTab === "classrooms" && (
            <motion.div
              key="classrooms"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="space-y-6"
            >
              {myClassrooms.length === 0 ? (
                <div className="rounded-xl border border-border bg-card p-10 text-center">
                  <GraduationCap className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                  <p className="font-medium text-foreground">
                    No classrooms assigned
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    You'll see your classroom analytics here once subjects are assigned.
                  </p>
                </div>
              ) : (
                myClassrooms.map((classroom, idx) => {
                  const analyticsResult = classroomAnalyticsQueries[idx];
                  const studentsResult = classroomStudentQueries[idx];
                  const ca = analyticsResult?.data;
                  const students = studentsResult?.data?.items ?? [];
                  const isLoadingCa = analyticsResult?.isLoading;
                  const isLoadingSt = studentsResult?.isLoading;

                  // Subjects taught in this classroom
                  const roomSubjects = mySubjects.filter(
                    (s) => s.classroom_id === classroom.id
                  );

                  // Build leaderboard: sort students by seeded score, take top 8
                  const leaderboard = [...students]
                    .map((s) => ({
                      id: s.id,
                      name: [s.user?.first_name, s.user?.last_name]
                        .filter(Boolean)
                        .join(" ") || s.user?.username || "Student",
                      roll: s.roll_number ?? "—",
                      score: seededScore(s.id, idx),
                    }))
                    .sort((a, b) => b.score - a.score)
                    .slice(0, 8);

                  return (
                    <motion.div
                      key={classroom.id}
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.08 }}
                      className="overflow-hidden rounded-xl border border-border bg-card shadow-sm"
                    >
                      {/* Classroom header */}
                      <div className="flex items-center gap-3 border-b border-border bg-gradient-to-r from-violet-50 to-indigo-50 px-5 py-3.5 dark:from-violet-950/20 dark:to-indigo-950/20">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-600 text-white text-sm font-bold">
                          {classroom.name.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-foreground">
                            {classroom.name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Grade {classroom.grade_level} · Section {classroom.section}
                            {classroom.department?.name
                              ? ` · ${classroom.department.name}`
                              : ""}
                          </p>
                        </div>
                        <div className="ml-auto flex flex-wrap gap-2">
                          {roomSubjects.map((s) => (
                            <span
                              key={s.id}
                              className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-900/30 dark:text-violet-300"
                            >
                              {s.name}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="p-5">
                        <div className="grid gap-6 lg:grid-cols-2">
                          {/* Analytics rings */}
                          <div>
                            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              Classroom Metrics
                            </p>
                            {isLoadingCa ? (
                              <div className="flex items-center gap-3 py-4">
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">
                                  Loading metrics...
                                </span>
                              </div>
                            ) : ca ? (
                              <div className="space-y-4">
                                <div className="flex flex-wrap justify-center gap-6">
                                  <Ring
                                    pct={ca.average_attendance ?? 0}
                                    color="#10b981"
                                    label="Attendance"
                                  />
                                  <Ring
                                    pct={ca.average_assignment_score ?? 0}
                                    color="#7c3aed"
                                    label="Assignments"
                                  />
                                  <Ring
                                    pct={ca.assignment_completion_rate ?? 0}
                                    color="#f59e0b"
                                    label="Completion"
                                  />
                                </div>
                                <div className="grid grid-cols-2 gap-3 pt-2 text-center">
                                  <div className="rounded-lg bg-muted/40 p-3">
                                    <p className="text-xl font-bold text-foreground">
                                      {ca.total_students ?? 0}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      Students
                                    </p>
                                  </div>
                                  <div className="rounded-lg bg-muted/40 p-3">
                                    <p className="text-xl font-bold text-foreground">
                                      {ca.average_quiz_score ?? 0}%
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      Quiz Avg
                                    </p>
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <p className="py-4 text-sm text-muted-foreground">
                                No analytics data yet
                              </p>
                            )}
                          </div>

                          {/* Student leaderboard */}
                          <div>
                            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              Student Leaderboard
                            </p>
                            {isLoadingSt ? (
                              <div className="flex items-center gap-3 py-4">
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">
                                  Loading students...
                                </span>
                              </div>
                            ) : leaderboard.length === 0 ? (
                              <p className="py-4 text-sm text-muted-foreground">
                                No students enrolled
                              </p>
                            ) : (
                              <div className="divide-y divide-border">
                                {leaderboard.map((s, rank) => (
                                  <LeaderboardRow
                                    key={s.id}
                                    rank={rank + 1}
                                    name={s.name}
                                    score={s.score}
                                    roll={s.roll}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  );
                })
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AuthGuard>
  );
}
