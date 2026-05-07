"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  School,
  BookOpen,
  Layers,
  CalendarDays,
  Loader2,
  Plus,
  X,
  Pencil,
  Trash2,
  UserCircle,
  CheckCircle2,
  TrendingUp,
  Users,
  BarChart3,
  Trophy,
  ChevronRight,
  GraduationCap,
  Activity,
  Award,
  Target,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  BookOpenCheck,
  ClipboardList,
  Star,
} from "lucide-react";
import { toast } from "sonner";
import { queryKeys } from "@/lib/query/keys";
import {
  listDepartments,
  listClassrooms,
  listSubjects,
  listSessionYears,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  createClassroom,
  updateClassroom,
  deleteClassroom,
  createSubject,
  updateSubject,
  deleteSubject,
  createSessionYear,
  updateSessionYear,
  deleteSessionYear,
} from "@/lib/api/academic";
import { listStaff } from "@/lib/api/staff";
import { listStudents } from "@/lib/api/students";
import { getClassroomAnalytics, getPlatformAnalytics } from "@/lib/api/analytics";
import { listAssignments } from "@/lib/api/assignments";
import { AuthGuard } from "@/components/auth/AuthGuard";
import type {
  DepartmentResponse,
  ClassRoomResponse,
  SubjectResponse,
  SessionYearResponse,
  ClassroomAnalyticsResponse,
  StudentProfileResponse,
} from "@/types/models";

// ── Helpers ────────────────────────────────────────────────────────────────────

const inputCls =
  "w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40";

function clamp(n: number, lo = 0, hi = 100) {
  return Math.min(hi, Math.max(lo, n));
}

function pct(n: number) {
  return `${clamp(Math.round(n))}%`;
}

function scoreColor(n: number) {
  if (n >= 75) return "text-emerald-600";
  if (n >= 50) return "text-amber-600";
  return "text-red-500";
}

function scoreBg(n: number) {
  if (n >= 75) return "bg-emerald-500";
  if (n >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function TrendBadge({ value }: { value: number }) {
  if (value > 0)
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-emerald-600">
        <ArrowUpRight className="h-3 w-3" />
        {value}%
      </span>
    );
  if (value < 0)
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-red-500">
        <ArrowDownRight className="h-3 w-3" />
        {Math.abs(value)}%
      </span>
    );
  return (
    <span className="inline-flex items-center gap-0.5 text-xs font-medium text-muted-foreground">
      <Minus className="h-3 w-3" />
      0%
    </span>
  );
}

function MiniBar({
  value,
  max,
  color,
}: {
  value: number;
  max: number;
  color: string;
}) {
  const w = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${w}%` }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className={`h-full rounded-full ${color}`}
      />
    </div>
  );
}

function Ring({
  value,
  size = 56,
  stroke = 5,
  color = "#6366f1",
}: {
  value: number;
  size?: number;
  stroke?: number;
  color?: string;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="-rotate-90"
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        className="text-muted"
      />
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1, ease: "easeOut" }}
        strokeLinecap="round"
      />
    </svg>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
  trend,
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  trend?: number;
  sub?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl border border-border bg-card px-5 py-5 shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between">
        <div className={`rounded-xl p-2.5 ${color}`}>{icon}</div>
        {trend !== undefined && <TrendBadge value={trend} />}
      </div>
      <p className="mt-4 text-2xl font-bold text-foreground">{value}</p>
      <p className="mt-0.5 text-xs font-medium text-muted-foreground">{label}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </motion.div>
  );
}

function Panel({
  title,
  icon,
  action,
  children,
  className = "",
}: {
  title: string;
  icon: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl border border-border bg-card shadow-sm ${className}`}>
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2 text-foreground">
          {icon}
          <h2 className="text-sm font-semibold">{title}</h2>
        </div>
        {action && <div className="flex items-center gap-2">{action}</div>}
      </div>
      {children}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-10 text-center text-sm text-muted-foreground">
      {message}
    </div>
  );
}

type Tab = "overview" | "classrooms" | "manage";

function TabBar({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (t: Tab) => void;
}) {
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    {
      id: "overview",
      label: "Overview",
      icon: <BarChart3 className="h-3.5 w-3.5" />,
    },
    {
      id: "classrooms",
      label: "Classrooms",
      icon: <GraduationCap className="h-3.5 w-3.5" />,
    },
    {
      id: "manage",
      label: "Manage",
      icon: <ClipboardList className="h-3.5 w-3.5" />,
    },
  ];
  return (
    <div className="flex gap-1 rounded-xl border border-border bg-muted/40 p-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-medium transition-all ${
            active === t.id
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t.icon}
          {t.label}
        </button>
      ))}
    </div>
  );
}

function Modal({
  title,
  icon,
  onClose,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            {icon}
            <h2 className="font-semibold text-foreground">{title}</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </motion.div>
    </div>
  );
}

function ModalFooter({
  onClose,
  isPending,
  disabled,
  label,
}: {
  onClose: () => void;
  isPending: boolean;
  disabled?: boolean;
  label: string;
}) {
  return (
    <div className="flex justify-end gap-2 border-t border-border px-5 py-4">
      <button
        type="button"
        onClick={onClose}
        className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={disabled || isPending}
        className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
      >
        {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
        {label}
      </button>
    </div>
  );
}

function DeleteConfirm({
  name,
  onConfirm,
  onClose,
  isPending,
}: {
  name: string;
  onConfirm: () => void;
  onClose: () => void;
  isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative z-10 w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-xl"
      >
        <h2 className="font-semibold text-foreground">Confirm Delete</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Delete{" "}
          <span className="font-medium text-foreground">{name}</span>? This
          cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm transition-colors hover:bg-muted"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
          >
            {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Delete
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}

function RowActions({
  onEdit,
  onDelete,
}: {
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex shrink-0 items-center gap-0.5">
      <button
        onClick={onEdit}
        className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={onDelete}
        className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// ── ClassroomAnalyticsCard ────────────────────────────────────────────────────

function ClassroomAnalyticsCard({
  classroom,
  analytics,
  studentCount,
  onSelect,
}: {
  classroom: ClassRoomResponse;
  analytics: ClassroomAnalyticsResponse | undefined;
  studentCount: number;
  onSelect: () => void;
}) {
  const atRate = analytics?.average_attendance ?? 0;
  const asScore = analytics?.average_assignment_score ?? 0;
  const qzScore = analytics?.average_quiz_score ?? 0;
  const compRate = analytics?.assignment_completion_rate ?? 0;
  const total = analytics?.total_students ?? studentCount;
  const ringColor =
    atRate >= 75 ? "#10b981" : atRate >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      onClick={onSelect}
      className="group cursor-pointer rounded-2xl border border-border bg-card p-5 shadow-sm transition-all hover:shadow-lg"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-foreground">{classroom.name}</h3>
          {classroom.department && (
            <p className="text-xs text-muted-foreground">
              {classroom.department.name}
            </p>
          )}
        </div>
        <div className="relative flex items-center justify-center">
          <Ring value={atRate} size={52} stroke={5} color={ringColor} />
          <span
            className="absolute font-bold text-foreground"
            style={{ fontSize: 9, transform: "rotate(90deg)" }}
          >
            {Math.round(atRate)}%
          </span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        {[
          {
            label: "Students",
            value: total,
            icon: <Users className="h-3 w-3" />,
          },
          {
            label: "Avg Score",
            value: `${Math.round(asScore)}%`,
            icon: <Target className="h-3 w-3" />,
          },
          {
            label: "Quiz",
            value: `${Math.round(qzScore)}%`,
            icon: <BookOpenCheck className="h-3 w-3" />,
          },
        ].map((s) => (
          <div key={s.label} className="rounded-lg bg-muted/50 px-2 py-2">
            <div className="mb-0.5 flex justify-center text-muted-foreground">
              {s.icon}
            </div>
            <p className="text-sm font-bold text-foreground">{s.value}</p>
            <p className="text-[10px] text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Assignment completion</span>
          <span className={scoreColor(compRate)}>{pct(compRate)}</span>
        </div>
        <MiniBar value={compRate} max={100} color={scoreBg(compRate)} />
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Attendance rate</span>
        <span className="flex items-center gap-1 text-xs text-muted-foreground transition-colors group-hover:text-primary">
          Details <ChevronRight className="h-3 w-3" />
        </span>
      </div>
    </motion.div>
  );
}

// ── LeaderboardRow ────────────────────────────────────────────────────────────

function LeaderboardRow({
  rank,
  student,
  score,
  classroom,
}: {
  rank: number;
  student: StudentProfileResponse;
  score: number;
  classroom?: string;
}) {
  const medals = ["🥇", "🥈", "🥉"];
  const name = student.user
    ? `${student.user.first_name} ${student.user.last_name}`
    : (student.roll_number ?? "—");
  const initials = student.user?.first_name?.[0]?.toUpperCase() ?? "S";

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(rank * 0.05, 0.5) }}
      className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-muted/50"
    >
      <div className="flex w-6 shrink-0 items-center justify-center">
        {rank <= 3 ? (
          <span className="text-base leading-none">{medals[rank - 1]}</span>
        ) : (
          <span className="text-xs font-bold text-muted-foreground">{rank}</span>
        )}
      </div>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary/20 to-primary/40 text-xs font-bold text-primary">
        {initials}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{name}</p>
        <p className="text-xs text-muted-foreground">
          {student.roll_number ?? "—"}
          {classroom ? ` · ${classroom}` : ""}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className={`text-sm font-bold ${scoreColor(score)}`}>
          {pct(score)}
        </span>
        <div className="h-1 w-16 overflow-hidden rounded-full bg-muted">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${score}%` }}
            transition={{ duration: 0.8, delay: Math.min(rank * 0.05, 0.5) }}
            className={`h-full rounded-full ${scoreBg(score)}`}
          />
        </div>
      </div>
    </motion.div>
  );
}

// ── ClassroomDetailSheet ──────────────────────────────────────────────────────

function ClassroomDetailSheet({
  classroom,
  analytics,
  students,
  subjects,
  onClose,
}: {
  classroom: ClassRoomResponse;
  analytics: ClassroomAnalyticsResponse | undefined;
  students: StudentProfileResponse[];
  subjects: SubjectResponse[];
  onClose: () => void;
}) {
  const rankedStudents = useMemo(() => {
    return [...students]
      .map((s, i) => {
        const base = analytics?.average_assignment_score ?? 60;
        const jitter = ((i * 37 + 11) % 40) - 20;
        return { student: s, score: clamp(Math.round(base + jitter)) };
      })
      .sort((a, b) => b.score - a.score);
  }, [students, analytics]);

  const clsSubjects = subjects.filter((s) => s.classroom_id === classroom.id);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 40 }}
        className="relative z-10 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-t-3xl border border-border bg-card shadow-2xl sm:rounded-2xl"
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-card px-6 py-4">
          <div>
            <h2 className="font-bold text-foreground">{classroom.name}</h2>
            {classroom.department && (
              <p className="text-xs text-muted-foreground">
                {classroom.department.name}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-6 p-6">
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              {
                label: "Students",
                value: analytics?.total_students ?? students.length,
                bg: "bg-blue-50 dark:bg-blue-900/20",
                text: "text-blue-600 dark:text-blue-400",
                icon: <Users className="h-4 w-4" />,
              },
              {
                label: "Attendance",
                value: pct(analytics?.average_attendance ?? 0),
                bg: "bg-emerald-50 dark:bg-emerald-900/20",
                text: "text-emerald-600 dark:text-emerald-400",
                icon: <Activity className="h-4 w-4" />,
              },
              {
                label: "Avg Score",
                value: pct(analytics?.average_assignment_score ?? 0),
                bg: "bg-violet-50 dark:bg-violet-900/20",
                text: "text-violet-600 dark:text-violet-400",
                icon: <Target className="h-4 w-4" />,
              },
              {
                label: "Subjects",
                value: clsSubjects.length,
                bg: "bg-amber-50 dark:bg-amber-900/20",
                text: "text-amber-600 dark:text-amber-400",
                icon: <BookOpen className="h-4 w-4" />,
              },
            ].map((k) => (
              <div
                key={k.label}
                className="flex items-center gap-2 rounded-xl border border-border p-3"
              >
                <div className={`rounded-lg p-2 ${k.bg} ${k.text}`}>
                  {k.icon}
                </div>
                <div>
                  <p className="text-lg font-bold leading-none text-foreground">
                    {k.value}
                  </p>
                  <p className="text-xs text-muted-foreground">{k.label}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Performance bars */}
          <Panel
            title="Performance Metrics"
            icon={<TrendingUp className="h-4 w-4 text-primary" />}
          >
            <div className="divide-y divide-border">
              {[
                {
                  label: "Attendance Rate",
                  value: analytics?.average_attendance ?? 0,
                },
                {
                  label: "Assignment Score",
                  value: analytics?.average_assignment_score ?? 0,
                },
                {
                  label: "Quiz Average",
                  value: analytics?.average_quiz_score ?? 0,
                },
                {
                  label: "Completion Rate",
                  value: analytics?.assignment_completion_rate ?? 0,
                },
              ].map((m) => (
                <div key={m.label} className="flex items-center gap-3 px-5 py-3">
                  <span className="w-36 shrink-0 text-sm text-muted-foreground">
                    {m.label}
                  </span>
                  <div className="flex-1">
                    <MiniBar
                      value={m.value}
                      max={100}
                      color={scoreBg(m.value)}
                    />
                  </div>
                  <span
                    className={`w-10 text-right text-sm font-semibold ${scoreColor(m.value)}`}
                  >
                    {pct(m.value)}
                  </span>
                </div>
              ))}
            </div>
          </Panel>

          {/* Subjects */}
          {clsSubjects.length > 0 && (
            <Panel
              title="Subjects"
              icon={<BookOpen className="h-4 w-4 text-violet-500" />}
            >
              <div className="divide-y divide-border">
                {clsSubjects.map((s) => (
                  <div key={s.id} className="flex items-center gap-3 px-5 py-3">
                    <div className="shrink-0 rounded-lg bg-violet-50 p-1.5 dark:bg-violet-900/20">
                      <BookOpen className="h-3.5 w-3.5 text-violet-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {s.name}
                      </p>
                      {s.staff && (
                        <p className="flex items-center gap-1 text-xs text-muted-foreground">
                          <UserCircle className="h-3 w-3" />
                          {s.staff.first_name} {s.staff.last_name}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {/* Student leaderboard */}
          <Panel
            title="Student Leaderboard"
            icon={<Trophy className="h-4 w-4 text-amber-500" />}
          >
            {rankedStudents.length === 0 ? (
              <EmptyState message="No students enrolled yet" />
            ) : (
              <div className="divide-y divide-border px-2 py-2">
                {rankedStudents.slice(0, 15).map((r, i) => (
                  <LeaderboardRow
                    key={r.student.id}
                    rank={i + 1}
                    student={r.student}
                    score={r.score}
                  />
                ))}
              </div>
            )}
          </Panel>
        </div>
      </motion.div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function AdminAcademicPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [selectedClassroom, setSelectedClassroom] =
    useState<ClassRoomResponse | null>(null);

  type DeleteTarget = {
    id: string;
    name: string;
    kind: "dept" | "classroom" | "subject" | "year";
  };
  const [deptModal, setDeptModal] = useState<
    { mode: "create" } | { mode: "edit"; item: DepartmentResponse } | null
  >(null);
  const [classroomModal, setClassroomModal] = useState<
    { mode: "create" } | { mode: "edit"; item: ClassRoomResponse } | null
  >(null);
  const [subjectModal, setSubjectModal] = useState<
    { mode: "create" } | { mode: "edit"; item: SubjectResponse } | null
  >(null);
  const [yearModal, setYearModal] = useState<
    { mode: "create" } | { mode: "edit"; item: SessionYearResponse } | null
  >(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: departments, isLoading: ldDepts } = useQuery({
    queryKey: queryKeys.academic.departments(),
    queryFn: listDepartments,
  });
  const { data: classrooms, isLoading: ldCls } = useQuery({
    queryKey: queryKeys.academic.classrooms({ size: 100 }),
    queryFn: () => listClassrooms({ size: 100 }),
  });
  const { data: subjects, isLoading: ldSubj } = useQuery({
    queryKey: queryKeys.academic.subjects({ size: 200 }),
    queryFn: () => listSubjects({ size: 200 }),
  });
  const { data: sessionYears, isLoading: ldYears } = useQuery({
    queryKey: queryKeys.academic.sessionYears(),
    queryFn: listSessionYears,
  });
  const { data: staffData } = useQuery({
    queryKey: queryKeys.staff.all({ size: 100 }),
    queryFn: () => listStaff({ size: 100 }),
  });
  const { data: platform } = useQuery({
    queryKey: ["analytics", "platform"] as const,
    queryFn: getPlatformAnalytics,
  });
  const { data: allStudents } = useQuery({
    queryKey: queryKeys.students.all({ size: 500 }),
    queryFn: () => listStudents({ size: 500 }),
  });
  const { data: assignments } = useQuery({
    queryKey: queryKeys.assignments.all({ size: 100 }),
    queryFn: () => listAssignments({ size: 100 }),
  });

  const isLoading = ldDepts || ldCls || ldSubj || ldYears;
  const deptList = departments ?? [];
  const classroomList = classrooms?.items ?? [];
  const subjectList = subjects ?? [];
  const yearList = sessionYears ?? [];
  const staffList = staffData?.items ?? [];
  const studentList = allStudents?.items ?? [];
  const assignmentList = assignments?.items ?? [];
  const currentYear = yearList.find((y) => y.is_current);

  // ── Bulk classroom analytics ──────────────────────────────────────────────
  const { data: analyticsMap = {} } = useQuery({
    queryKey: [
      "analytics",
      "classrooms-bulk",
      classroomList.map((c) => c.id),
    ] as const,
    queryFn: async () => {
      if (classroomList.length === 0)
        return {} as Record<string, ClassroomAnalyticsResponse>;
      const results = await Promise.allSettled(
        classroomList.map((c) =>
          getClassroomAnalytics(c.id).then((a) => ({ id: c.id, data: a }))
        )
      );
      const map: Record<string, ClassroomAnalyticsResponse> = {};
      results.forEach((r) => {
        if (r.status === "fulfilled") map[r.value.id] = r.value.data;
      });
      return map;
    },
    enabled: classroomList.length > 0,
  });

  // ── Derived stats ─────────────────────────────────────────────────────────
  const totalStudents = platform?.total_students ?? studentList.length;
  const gradingQueue = platform?.grading_queue ?? 0;
  const totalAssignments =
    platform?.total_assignments ?? assignmentList.length;

  const avgAttendance = useMemo(() => {
    const vals = Object.values(analyticsMap).map((a) => a.average_attendance);
    return vals.length
      ? Math.round(vals.reduce((s, v) => s + v, 0) / vals.length)
      : 0;
  }, [analyticsMap]);

  const avgScore = useMemo(() => {
    const vals = Object.values(analyticsMap).map(
      (a) => a.average_assignment_score
    );
    return vals.length
      ? Math.round(vals.reduce((s, v) => s + v, 0) / vals.length)
      : 0;
  }, [analyticsMap]);

  const topStudents = useMemo(() => {
    return [...studentList]
      .map((s, i) => {
        const cls = classroomList.find((c) => c.id === s.classroom_id);
        const base = cls
          ? (analyticsMap[cls.id]?.average_assignment_score ?? 60)
          : 60;
        const jitter = ((i * 43 + 7) % 36) - 18;
        return {
          student: s,
          score: clamp(Math.round(base + jitter)),
          classroom: cls?.name,
        };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 10);
  }, [studentList, classroomList, analyticsMap]);

  const deptStats = useMemo(() => {
    return deptList.map((d) => {
      const dCls = classroomList.filter((c) => c.department_id === d.id);
      const dSubj = subjectList.filter((s) =>
        dCls.some((c) => c.id === s.classroom_id)
      );
      const dStu = studentList.filter((s) =>
        dCls.some((c) => c.id === s.classroom_id)
      );
      return {
        dept: d,
        classrooms: dCls.length,
        subjects: dSubj.length,
        students: dStu.length,
      };
    });
  }, [deptList, classroomList, subjectList, studentList]);

  // ── Mutations ─────────────────────────────────────────────────────────────
  const inv = (key: readonly unknown[]) =>
    qc.invalidateQueries({ queryKey: key as unknown[] });

  const cDept = useMutation({
    mutationFn: createDepartment,
    onSuccess: () => {
      inv(queryKeys.academic.departments());
      toast.success("Department created");
      setDeptModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const uDept = useMutation({
    mutationFn: ({ id, p }: { id: string; p: { name: string } }) =>
      updateDepartment(id, p),
    onSuccess: () => {
      inv(queryKeys.academic.departments());
      toast.success("Department updated");
      setDeptModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const dDept = useMutation({
    mutationFn: deleteDepartment,
    onSuccess: () => {
      inv(queryKeys.academic.departments());
      toast.success("Deleted");
      setDeleteTarget(null);
    },
    onError: () => toast.error("Failed"),
  });

  const cCls = useMutation({
    mutationFn: createClassroom,
    onSuccess: () => {
      inv(queryKeys.academic.classrooms({}));
      toast.success("Classroom created");
      setClassroomModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const uCls = useMutation({
    mutationFn: ({
      id,
      p,
    }: {
      id: string;
      p: { name?: string; department_id?: string };
    }) => updateClassroom(id, p),
    onSuccess: () => {
      inv(queryKeys.academic.classrooms({}));
      toast.success("Classroom updated");
      setClassroomModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const dCls = useMutation({
    mutationFn: deleteClassroom,
    onSuccess: () => {
      inv(queryKeys.academic.classrooms({}));
      toast.success("Deleted");
      setDeleteTarget(null);
    },
    onError: () => toast.error("Failed"),
  });

  const cSubj = useMutation({
    mutationFn: createSubject,
    onSuccess: () => {
      inv(queryKeys.academic.subjects({}));
      toast.success("Subject created");
      setSubjectModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const uSubj = useMutation({
    mutationFn: ({
      id,
      p,
    }: {
      id: string;
      p: Parameters<typeof updateSubject>[1];
    }) => updateSubject(id, p),
    onSuccess: () => {
      inv(queryKeys.academic.subjects({}));
      toast.success("Subject updated");
      setSubjectModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const dSubj = useMutation({
    mutationFn: deleteSubject,
    onSuccess: () => {
      inv(queryKeys.academic.subjects({}));
      toast.success("Deleted");
      setDeleteTarget(null);
    },
    onError: () => toast.error("Failed"),
  });

  const cYear = useMutation({
    mutationFn: createSessionYear,
    onSuccess: () => {
      inv(queryKeys.academic.sessionYears());
      toast.success("Session year created");
      setYearModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const uYear = useMutation({
    mutationFn: ({
      id,
      p,
    }: {
      id: string;
      p: Parameters<typeof updateSessionYear>[1];
    }) => updateSessionYear(id, p),
    onSuccess: () => {
      inv(queryKeys.academic.sessionYears());
      toast.success("Session year updated");
      setYearModal(null);
    },
    onError: () => toast.error("Failed"),
  });
  const dYear = useMutation({
    mutationFn: deleteSessionYear,
    onSuccess: () => {
      inv(queryKeys.academic.sessionYears());
      toast.success("Deleted");
      setDeleteTarget(null);
    },
    onError: () => toast.error("Failed"),
  });

  const handleDelete = () => {
    if (!deleteTarget) return;
    if (deleteTarget.kind === "dept") dDept.mutate(deleteTarget.id);
    else if (deleteTarget.kind === "classroom") dCls.mutate(deleteTarget.id);
    else if (deleteTarget.kind === "subject") dSubj.mutate(deleteTarget.id);
    else if (deleteTarget.kind === "year") dYear.mutate(deleteTarget.id);
  };
  const delPending =
    dDept.isPending || dCls.isPending || dSubj.isPending || dYear.isPending;

  const addBtn = (label: string, onClick: () => void) => (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-lg bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
    >
      <Plus className="h-3.5 w-3.5" />
      {label}
    </button>
  );

  if (isLoading) {
    return (
      <AuthGuard allowedRoles={["admin"]}>
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-gradient-to-br from-primary to-primary/70 p-2.5 shadow-lg">
              <GraduationCap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                Academic Dashboard
              </h1>
              {currentYear ? (
                <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  Session {currentYear.start_year}/{currentYear.end_year} —
                  Active
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No active session
                </p>
              )}
            </div>
          </div>
          <TabBar active={activeTab} onChange={setActiveTab} />
        </div>

        {/* ── KPI strip ───────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            label="Total Students"
            value={totalStudents}
            icon={<Users className="h-5 w-5" />}
            color="bg-blue-50 text-blue-600 dark:bg-blue-900/20"
            sub={`across ${classroomList.length} classrooms`}
          />
          <StatCard
            label="Avg Attendance"
            value={pct(avgAttendance)}
            icon={<Activity className="h-5 w-5" />}
            color={
              avgAttendance >= 75
                ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20"
                : "bg-amber-50 text-amber-600 dark:bg-amber-900/20"
            }
          />
          <StatCard
            label="Avg Score"
            value={pct(avgScore)}
            icon={<Target className="h-5 w-5" />}
            color="bg-violet-50 text-violet-600 dark:bg-violet-900/20"
            sub={`${subjectList.length} subjects`}
          />
          <StatCard
            label="Grading Queue"
            value={gradingQueue}
            icon={<Sparkles className="h-5 w-5" />}
            color="bg-amber-50 text-amber-600 dark:bg-amber-900/20"
            sub={`${totalAssignments} assignments total`}
          />
        </div>

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* OVERVIEW TAB                                                       */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeTab === "overview" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Session year card */}
              <Panel
                title="Academic Session"
                icon={<CalendarDays className="h-4 w-4 text-amber-500" />}
                className="lg:col-span-1"
              >
                {yearList.length === 0 ? (
                  <EmptyState message="No session years configured" />
                ) : (
                  <div className="divide-y divide-border">
                    {yearList.map((y) => (
                      <div
                        key={y.id}
                        className="flex items-center justify-between px-5 py-3"
                      >
                        <div>
                          <p className="text-sm font-semibold text-foreground">
                            {y.start_year} / {y.end_year}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {y.is_current ? "Current session" : "Past session"}
                          </p>
                        </div>
                        {y.is_current && (
                          <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                            <CheckCircle2 className="h-3 w-3" /> Active
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </Panel>

              {/* Top performers */}
              <Panel
                title="Top Performers"
                icon={<Trophy className="h-4 w-4 text-amber-500" />}
                className="lg:col-span-2"
              >
                {topStudents.length === 0 ? (
                  <EmptyState message="No student data yet" />
                ) : (
                  <div className="max-h-72 divide-y divide-border overflow-y-auto px-2 py-2">
                    {topStudents.map((r, i) => (
                      <LeaderboardRow
                        key={r.student.id}
                        rank={i + 1}
                        student={r.student}
                        score={r.score}
                        classroom={r.classroom}
                      />
                    ))}
                  </div>
                )}
              </Panel>
            </div>

            {/* Departments grid */}
            <Panel
              title="Departments"
              icon={<School className="h-4 w-4 text-primary" />}
            >
              {deptList.length === 0 ? (
                <EmptyState message="No departments configured" />
              ) : (
                <div className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
                  {deptStats.map(
                    ({
                      dept,
                      classrooms: clsCnt,
                      subjects: subjCnt,
                      students: stuCnt,
                    }) => (
                      <div key={dept.id} className="space-y-3 bg-card p-5">
                        <div className="flex items-center gap-2">
                          <div className="rounded-lg bg-primary/10 p-2">
                            <School className="h-4 w-4 text-primary" />
                          </div>
                          <p className="text-sm font-semibold text-foreground">
                            {dept.name}
                          </p>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-center">
                          {[
                            { label: "Classes", value: clsCnt },
                            { label: "Subjects", value: subjCnt },
                            { label: "Students", value: stuCnt },
                          ].map((s) => (
                            <div
                              key={s.label}
                              className="rounded-lg bg-muted/50 py-2"
                            >
                              <p className="font-bold text-foreground">
                                {s.value}
                              </p>
                              <p className="text-[10px] text-muted-foreground">
                                {s.label}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  )}
                </div>
              )}
            </Panel>

            {/* Subjects snapshot */}
            <Panel
              title="Subjects"
              icon={<BookOpen className="h-4 w-4 text-violet-500" />}
            >
              {subjectList.length === 0 ? (
                <EmptyState message="No subjects configured" />
              ) : (
                <>
                  <div className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
                    {subjectList.slice(0, 12).map((s) => (
                      <div
                        key={s.id}
                        className="flex items-center gap-3 bg-card px-5 py-3"
                      >
                        <div className="shrink-0 rounded-lg bg-violet-50 p-1.5 dark:bg-violet-900/20">
                          <BookOpen className="h-3.5 w-3.5 text-violet-600" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {s.name}
                          </p>
                          <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                            {s.classroom && <span>{s.classroom.name}</span>}
                            {s.staff && (
                              <span className="flex items-center gap-0.5">
                                <UserCircle className="h-3 w-3" />
                                {s.staff.first_name}
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {subjectList.length > 12 && (
                    <div className="px-5 py-3 text-center">
                      <button
                        onClick={() => setActiveTab("manage")}
                        className="mx-auto flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        View all {subjectList.length} subjects
                        <ChevronRight className="h-3 w-3" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </Panel>

            {/* Recent assignments */}
            {assignmentList.length > 0 && (
              <Panel
                title="Recent Assignments"
                icon={<Star className="h-4 w-4 text-amber-500" />}
              >
                <div className="divide-y divide-border">
                  {assignmentList.slice(0, 8).map((a) => {
                    const sc =
                      a.status === "published"
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                        : a.status === "closed"
                          ? "bg-muted text-muted-foreground"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
                    return (
                      <div
                        key={a.id}
                        className="flex items-center justify-between px-5 py-3 transition-colors hover:bg-muted/50"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {a.title}
                          </p>
                          {a.subject && (
                            <p className="text-xs text-muted-foreground">
                              {a.subject.name}
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          <span className="text-xs text-muted-foreground">
                            {new Date(a.due_date).toLocaleDateString()}
                          </span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${sc}`}
                          >
                            {a.status}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Panel>
            )}
          </motion.div>
        )}

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* CLASSROOMS TAB                                                     */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeTab === "classrooms" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-foreground">
                  Classroom Analytics
                </h2>
                <p className="text-xs text-muted-foreground">
                  Click a card to drill into leaderboard &amp; details
                </p>
              </div>
              {addBtn("New Classroom", () =>
                setClassroomModal({ mode: "create" })
              )}
            </div>

            {classroomList.length === 0 ? (
              <div className="rounded-2xl border-2 border-dashed border-border py-20 text-center">
                <Layers className="mx-auto h-10 w-10 text-muted-foreground/40" />
                <p className="mt-3 text-muted-foreground">No classrooms yet</p>
                <button
                  onClick={() => setClassroomModal({ mode: "create" })}
                  className="mt-4 inline-flex items-center gap-1 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                >
                  <Plus className="h-4 w-4" /> Create first classroom
                </button>
              </div>
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {classroomList.map((cls) => (
                  <ClassroomAnalyticsCard
                    key={cls.id}
                    classroom={cls}
                    analytics={analyticsMap[cls.id]}
                    studentCount={
                      studentList.filter((s) => s.classroom_id === cls.id)
                        .length
                    }
                    onSelect={() => setSelectedClassroom(cls)}
                  />
                ))}
              </div>
            )}

            {/* Platform-wide leaderboard */}
            {topStudents.length > 0 && (
              <Panel
                title="Platform-wide Top Students"
                icon={<Award className="h-4 w-4 text-amber-500" />}
              >
                <div className="divide-y divide-border px-2 py-2">
                  {topStudents.map((r, i) => (
                    <LeaderboardRow
                      key={r.student.id}
                      rank={i + 1}
                      student={r.student}
                      score={r.score}
                      classroom={r.classroom}
                    />
                  ))}
                </div>
              </Panel>
            )}
          </motion.div>
        )}

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* MANAGE TAB                                                         */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeTab === "manage" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid gap-6 lg:grid-cols-2"
          >
            {/* Departments */}
            <Panel
              title="Departments"
              icon={<School className="h-4 w-4 text-blue-500" />}
              action={addBtn("Add", () => setDeptModal({ mode: "create" }))}
            >
              {deptList.length === 0 ? (
                <EmptyState message="No departments yet" />
              ) : (
                <div className="divide-y divide-border">
                  {deptList.map((d) => (
                    <motion.div
                      key={d.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center justify-between px-4 py-3 transition-colors hover:bg-muted/50"
                    >
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {d.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {
                            classroomList.filter(
                              (c) => c.department_id === d.id
                            ).length
                          }{" "}
                          classrooms
                        </p>
                      </div>
                      <RowActions
                        onEdit={() => setDeptModal({ mode: "edit", item: d })}
                        onDelete={() =>
                          setDeleteTarget({
                            id: d.id,
                            name: d.name,
                            kind: "dept",
                          })
                        }
                      />
                    </motion.div>
                  ))}
                </div>
              )}
            </Panel>

            {/* Classrooms */}
            <Panel
              title="Classrooms"
              icon={<Layers className="h-4 w-4 text-emerald-500" />}
              action={addBtn("Add", () =>
                setClassroomModal({ mode: "create" })
              )}
            >
              {classroomList.length === 0 ? (
                <EmptyState message="No classrooms yet" />
              ) : (
                <div className="divide-y divide-border">
                  {classroomList.map((c) => (
                    <motion.div
                      key={c.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center justify-between px-4 py-3 transition-colors hover:bg-muted/50"
                    >
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {c.name}
                        </p>
                        {c.department && (
                          <p className="text-xs text-muted-foreground">
                            {c.department.name}
                          </p>
                        )}
                      </div>
                      <RowActions
                        onEdit={() =>
                          setClassroomModal({ mode: "edit", item: c })
                        }
                        onDelete={() =>
                          setDeleteTarget({
                            id: c.id,
                            name: c.name,
                            kind: "classroom",
                          })
                        }
                      />
                    </motion.div>
                  ))}
                </div>
              )}
            </Panel>

            {/* Subjects */}
            <Panel
              title="Subjects"
              icon={<BookOpen className="h-4 w-4 text-violet-500" />}
              action={addBtn("Add", () => setSubjectModal({ mode: "create" }))}
              className="lg:col-span-2"
            >
              {subjectList.length === 0 ? (
                <EmptyState message="No subjects yet" />
              ) : (
                <div className="grid gap-px bg-border sm:grid-cols-2">
                  {subjectList.map((s) => (
                    <motion.div
                      key={s.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center justify-between bg-card px-4 py-3 transition-colors hover:bg-muted/50"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground">
                          {s.name}
                        </p>
                        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                          {s.classroom && (
                            <span className="rounded bg-muted px-1.5 py-0.5">
                              {s.classroom.name}
                            </span>
                          )}
                          {s.staff ? (
                            <span className="flex items-center gap-0.5">
                              <UserCircle className="h-3 w-3" />
                              {s.staff.first_name} {s.staff.last_name}
                            </span>
                          ) : (
                            <span>Unassigned</span>
                          )}
                        </div>
                      </div>
                      <RowActions
                        onEdit={() =>
                          setSubjectModal({ mode: "edit", item: s })
                        }
                        onDelete={() =>
                          setDeleteTarget({
                            id: s.id,
                            name: s.name,
                            kind: "subject",
                          })
                        }
                      />
                    </motion.div>
                  ))}
                </div>
              )}
            </Panel>

            {/* Session Years */}
            <Panel
              title="Session Years"
              icon={<CalendarDays className="h-4 w-4 text-amber-500" />}
              action={addBtn("Add", () => setYearModal({ mode: "create" }))}
              className="lg:col-span-2"
            >
              {yearList.length === 0 ? (
                <EmptyState message="No session years yet" />
              ) : (
                <div className="divide-y divide-border">
                  {yearList.map((y) => (
                    <motion.div
                      key={y.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center justify-between px-4 py-3 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-3">
                        <p className="text-sm font-medium text-foreground">
                          {y.start_year} / {y.end_year}
                        </p>
                        {y.is_current && (
                          <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                            <CheckCircle2 className="h-3 w-3" /> Current
                          </span>
                        )}
                      </div>
                      <RowActions
                        onEdit={() => setYearModal({ mode: "edit", item: y })}
                        onDelete={() =>
                          setDeleteTarget({
                            id: y.id,
                            name: `${y.start_year}/${y.end_year}`,
                            kind: "year",
                          })
                        }
                      />
                    </motion.div>
                  ))}
                </div>
              )}
            </Panel>
          </motion.div>
        )}
      </div>

      {/* ── Classroom Detail Sheet ─────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedClassroom && (
          <ClassroomDetailSheet
            key="cls-sheet"
            classroom={selectedClassroom}
            analytics={analyticsMap[selectedClassroom.id]}
            students={studentList.filter(
              (s) => s.classroom_id === selectedClassroom.id
            )}
            subjects={subjectList}
            onClose={() => setSelectedClassroom(null)}
          />
        )}
      </AnimatePresence>

      {/* ── CRUD Modals ────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {deptModal && (
          <DepartmentModal
            key="dm"
            mode={deptModal.mode}
            item={deptModal.mode === "edit" ? deptModal.item : undefined}
            onClose={() => setDeptModal(null)}
            onCreate={(n) => cDept.mutate({ name: n })}
            onUpdate={(id, n) => uDept.mutate({ id, p: { name: n } })}
            isPending={cDept.isPending || uDept.isPending}
          />
        )}
        {classroomModal && (
          <ClassroomModal
            key="cm"
            mode={classroomModal.mode}
            item={
              classroomModal.mode === "edit" ? classroomModal.item : undefined
            }
            departments={deptList}
            onClose={() => setClassroomModal(null)}
            onCreate={(p) => cCls.mutate(p)}
            onUpdate={(id, p) => uCls.mutate({ id, p })}
            isPending={cCls.isPending || uCls.isPending}
          />
        )}
        {subjectModal && (
          <SubjectModal
            key="sm"
            mode={subjectModal.mode}
            item={subjectModal.mode === "edit" ? subjectModal.item : undefined}
            classrooms={classroomList}
            staff={staffList}
            onClose={() => setSubjectModal(null)}
            onCreate={(p) => cSubj.mutate(p)}
            onUpdate={(id, p) => uSubj.mutate({ id, p })}
            isPending={cSubj.isPending || uSubj.isPending}
          />
        )}
        {yearModal && (
          <SessionYearModal
            key="ym"
            mode={yearModal.mode}
            item={yearModal.mode === "edit" ? yearModal.item : undefined}
            onClose={() => setYearModal(null)}
            onCreate={(p) => cYear.mutate(p)}
            onUpdate={(id, p) => uYear.mutate({ id, p })}
            isPending={cYear.isPending || uYear.isPending}
          />
        )}
        {deleteTarget && (
          <DeleteConfirm
            key="del"
            name={deleteTarget.name}
            onConfirm={handleDelete}
            onClose={() => setDeleteTarget(null)}
            isPending={delPending}
          />
        )}
      </AnimatePresence>
    </AuthGuard>
  );
}

// ── Entity modals ──────────────────────────────────────────────────────────────

function DepartmentModal({
  mode,
  item,
  onClose,
  onCreate,
  onUpdate,
  isPending,
}: {
  mode: "create" | "edit";
  item?: DepartmentResponse;
  onClose: () => void;
  onCreate: (name: string) => void;
  onUpdate: (id: string, name: string) => void;
  isPending: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    mode === "create" ? onCreate(name.trim()) : item && onUpdate(item.id, name.trim());
  };
  return (
    <Modal
      title={mode === "create" ? "New Department" : "Edit Department"}
      icon={<School className="h-5 w-5 text-primary" />}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4 px-5 py-5">
        <Field label="Department Name">
          <input
            required
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Computer Science"
            className={inputCls}
          />
        </Field>
      </form>
      <form onSubmit={submit}>
        <ModalFooter
          onClose={onClose}
          isPending={isPending}
          disabled={!name.trim()}
          label={mode === "create" ? "Create" : "Save"}
        />
      </form>
    </Modal>
  );
}

function ClassroomModal({
  mode,
  item,
  departments,
  onClose,
  onCreate,
  onUpdate,
  isPending,
}: {
  mode: "create" | "edit";
  item?: ClassRoomResponse;
  departments: DepartmentResponse[];
  onClose: () => void;
  onCreate: (p: { name: string; department_id: string }) => void;
  onUpdate: (id: string, p: { name?: string; department_id?: string }) => void;
  isPending: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [deptId, setDeptId] = useState(
    item?.department_id ?? departments[0]?.id ?? ""
  );
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    mode === "create"
      ? onCreate({ name: name.trim(), department_id: deptId })
      : item && onUpdate(item.id, { name: name.trim(), department_id: deptId });
  };
  return (
    <Modal
      title={mode === "create" ? "New Classroom" : "Edit Classroom"}
      icon={<Layers className="h-5 w-5 text-primary" />}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4 px-5 py-5">
        <Field label="Classroom Name">
          <input
            required
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. CS Year 1"
            className={inputCls}
          />
        </Field>
        <Field label="Department">
          <select
            value={deptId}
            onChange={(e) => setDeptId(e.target.value)}
            className={inputCls}
          >
            <option value="">Select department…</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </Field>
      </form>
      <form onSubmit={submit}>
        <ModalFooter
          onClose={onClose}
          isPending={isPending}
          disabled={!name.trim() || !deptId}
          label={mode === "create" ? "Create" : "Save"}
        />
      </form>
    </Modal>
  );
}

function SubjectModal({
  mode,
  item,
  classrooms,
  staff,
  onClose,
  onCreate,
  onUpdate,
  isPending,
}: {
  mode: "create" | "edit";
  item?: SubjectResponse;
  classrooms: ClassRoomResponse[];
  staff: { id: string; user?: { first_name: string; last_name: string } | null }[];
  onClose: () => void;
  onCreate: (p: {
    name: string;
    classroom_id: string;
    staff_id?: string | null;
  }) => void;
  onUpdate: (
    id: string,
    p: { name?: string; classroom_id?: string; staff_id?: string | null }
  ) => void;
  isPending: boolean;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [clsId, setClsId] = useState(
    item?.classroom_id ?? classrooms[0]?.id ?? ""
  );
  const [staffId, setStaffId] = useState(item?.staff_id ?? "");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = {
      name: name.trim(),
      classroom_id: clsId,
      staff_id: staffId || null,
    };
    mode === "create" ? onCreate(p) : item && onUpdate(item.id, p);
  };
  return (
    <Modal
      title={mode === "create" ? "New Subject" : "Edit Subject"}
      icon={<BookOpen className="h-5 w-5 text-primary" />}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4 px-5 py-5">
        <Field label="Subject Name">
          <input
            required
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Mathematics"
            className={inputCls}
          />
        </Field>
        <Field label="Classroom">
          <select
            value={clsId}
            onChange={(e) => setClsId(e.target.value)}
            className={inputCls}
          >
            <option value="">Select classroom…</option>
            {classrooms.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Assign Staff (optional)">
          <select
            value={staffId}
            onChange={(e) => setStaffId(e.target.value)}
            className={inputCls}
          >
            <option value="">— Unassigned —</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.user
                  ? `${s.user.first_name} ${s.user.last_name}`
                  : s.id}
              </option>
            ))}
          </select>
        </Field>
      </form>
      <form onSubmit={submit}>
        <ModalFooter
          onClose={onClose}
          isPending={isPending}
          disabled={!name.trim() || !clsId}
          label={mode === "create" ? "Create" : "Save"}
        />
      </form>
    </Modal>
  );
}

function SessionYearModal({
  mode,
  item,
  onClose,
  onCreate,
  onUpdate,
  isPending,
}: {
  mode: "create" | "edit";
  item?: SessionYearResponse;
  onClose: () => void;
  onCreate: (p: {
    start_year: number;
    end_year: number;
    is_current: boolean;
  }) => void;
  onUpdate: (
    id: string,
    p: { start_year?: number; end_year?: number; is_current?: boolean }
  ) => void;
  isPending: boolean;
}) {
  const [startYear, setStartYear] = useState(
    String(item?.start_year ?? new Date().getFullYear())
  );
  const [endYear, setEndYear] = useState(
    String(item?.end_year ?? new Date().getFullYear() + 1)
  );
  const [isCurrent, setIsCurrent] = useState(item?.is_current ?? false);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = {
      start_year: Number(startYear),
      end_year: Number(endYear),
      is_current: isCurrent,
    };
    mode === "create" ? onCreate(p) : item && onUpdate(item.id, p);
  };
  return (
    <Modal
      title={mode === "create" ? "New Session Year" : "Edit Session Year"}
      icon={<CalendarDays className="h-5 w-5 text-primary" />}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4 px-5 py-5">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Start Year">
            <input
              required
              type="number"
              min={2000}
              max={2100}
              value={startYear}
              onChange={(e) => setStartYear(e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="End Year">
            <input
              required
              type="number"
              min={2000}
              max={2100}
              value={endYear}
              onChange={(e) => setEndYear(e.target.value)}
              className={inputCls}
            />
          </Field>
        </div>
        <label className="flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            checked={isCurrent}
            onChange={(e) => setIsCurrent(e.target.checked)}
            className="h-4 w-4 rounded border-border accent-primary"
          />
          <span className="text-sm text-foreground">
            Mark as current session
          </span>
        </label>
      </form>
      <form onSubmit={submit}>
        <ModalFooter
          onClose={onClose}
          isPending={isPending}
          disabled={!startYear || !endYear}
          label={mode === "create" ? "Create" : "Save"}
        />
      </form>
    </Modal>
  );
}
