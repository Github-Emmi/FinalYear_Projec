"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users, GraduationCap, UserCheck, School,
  ClipboardList, BookOpen, TrendingUp, Brain,
  Activity, Wifi, Cpu, AlertTriangle, CheckCircle2,
  ChevronRight, BarChart3,
} from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from "recharts";
import { queryKeys } from "@/lib/query/keys";
import { getPlatformAnalytics } from "@/lib/api/analytics";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils/cn";
import Link from "next/link";

// ── Sparkline generator (mock trend) ──────────────────────────────────────────
function mkSparkline(base: number, points = 8) {
  return Array.from({ length: points }, (_, i) => ({
    i,
    v: Math.max(0, base + Math.round((Math.random() - 0.4) * base * 0.15 * (i + 1))),
  }));
}

// ── AI Queue store (driven by WS events) ─────────────────────────────────────
import { create } from "zustand";
interface AIQueueStore { count: number; inc: () => void; dec: () => void; set: (n: number) => void }
const useAIQueue = create<AIQueueStore>((set) => ({
  count: 0,
  inc: () => set((s) => ({ count: s.count + 1 })),
  dec: () => set((s) => ({ count: Math.max(0, s.count - 1) })),
  set: (n) => set({ count: n }),
}));

// ── Pulse dot ────────────────────────────────────────────────────────────────
function Pulse({ color = "bg-emerald-500" }: { color?: string }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-75", color)} />
      <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", color)} />
    </span>
  );
}

// ── Metric KPI Card ───────────────────────────────────────────────────────────
interface KPICardProps {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  trend?: string;
  trendUp?: boolean;
  sparkData?: { i: number; v: number }[];
  delay?: number;
  href?: string;
}

function KPICard({ label, value, icon: Icon, color, bgColor, trend, trendUp, sparkData, delay = 0, href }: KPICardProps) {
  const inner = (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35, ease: "easeOut" }}
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-border bg-card p-5 shadow-sm transition-all hover:shadow-md",
        href && "cursor-pointer hover:border-primary/40"
      )}
    >
      {/* Background glow */}
      <div className={cn("absolute -right-4 -top-4 h-20 w-20 rounded-full opacity-10 blur-2xl", bgColor)} />

      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className="text-3xl font-bold tabular-nums text-foreground">{value}</p>
          {trend && (
            <p className={cn("flex items-center gap-1 text-xs font-medium", trendUp ? "text-emerald-500" : "text-red-500")}>
              <TrendingUp className={cn("h-3 w-3", !trendUp && "rotate-180")} />
              {trend}
            </p>
          )}
        </div>
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl shadow-sm", bgColor)}>
          <Icon className={cn("h-5 w-5", color)} />
        </div>
      </div>

      {sparkData && (
        <div className="mt-3 h-12">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="currentColor" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="currentColor" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke="currentColor" strokeWidth={1.5}
                fill={`url(#spark-${label})`} className={color} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {href && (
        <ChevronRight className="absolute bottom-4 right-4 h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      )}
    </motion.div>
  );

  return href ? <Link href={href}>{inner}</Link> : inner;
}

// ── AI Queue Badge ────────────────────────────────────────────────────────────
function AIQueueBadge({ initialCount }: { initialCount: number }) {
  const { count, set } = useAIQueue();
  useEffect(() => { set(initialCount); }, [initialCount, set]);

  return (
    <motion.div
      animate={count > 0 ? { boxShadow: ["0 0 0 0 rgba(59,130,246,0)", "0 0 0 8px rgba(59,130,246,0.15)", "0 0 0 0 rgba(59,130,246,0)"] } : {}}
      transition={{ repeat: count > 0 ? Infinity : 0, duration: 2 }}
      className={cn(
        "flex items-center gap-3 rounded-2xl border p-4 transition-colors",
        count > 0 ? "border-blue-500/40 bg-blue-500/10" : "border-border bg-card"
      )}
    >
      <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", count > 0 ? "bg-blue-500/20" : "bg-muted")}>
        <Brain className={cn("h-5 w-5", count > 0 ? "text-blue-500" : "text-muted-foreground")} />
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">AI Grading Queue</p>
        <AnimatePresence mode="wait">
          {count > 0 ? (
            <motion.p key="active" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}
              className="flex items-center gap-1.5 text-sm font-semibold text-blue-500">
              <Pulse color="bg-blue-500" />
              AI Grading {count} {count === 1 ? "submission" : "submissions"}…
            </motion.p>
          ) : (
            <motion.p key="idle" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}
              className="text-sm font-medium text-muted-foreground">
              AI Brain Idle
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ── Staff Load bar ────────────────────────────────────────────────────────────
function StaffLoadBar({ students, staff }: { students: number; staff: number }) {
  const ratio = staff > 0 ? students / staff : 0;
  const pct = Math.min(100, (ratio / 40) * 100); // 40:1 = full
  const color = pct < 60 ? "bg-emerald-500" : pct < 85 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-500/15">
            <Activity className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Staff Load</p>
            <p className="text-2xl font-bold tabular-nums">{ratio.toFixed(1)}<span className="ml-1 text-sm font-normal text-muted-foreground">:1</span></p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">{students} students / {staff} staff</p>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: "easeOut" }}
          className={cn("h-full rounded-full", color)} />
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">{pct < 60 ? "Healthy ratio" : pct < 85 ? "Moderate load" : "High load"}</p>
    </div>
  );
}

// ── System Status panel ───────────────────────────────────────────────────────
function SystemStatus() {
  const [apiPing, setApiPing] = useState<number | null>(null);
  const [apiOk, setApiOk] = useState(true);

  useEffect(() => {
    const measure = async () => {
      const t0 = performance.now();
      try {
        const res = await fetch("/api/v1/health", { method: "GET" }).catch(() => null);
        const ms = Math.round(performance.now() - t0);
        setApiPing(ms);
        setApiOk(!!res && res.ok);
      } catch {
        setApiOk(false);
      }
    };
    measure();
    const id = setInterval(measure, 30_000);
    return () => clearInterval(id);
  }, []);

  const statuses = [
    {
      label: "API",
      detail: apiPing !== null ? `Online (${apiPing}ms)` : "Connecting…",
      ok: apiOk,
      icon: Wifi,
    },
    { label: "Worker", detail: "Active", ok: true, icon: Cpu },
    { label: "AI", detail: "openrouter/free", ok: true, icon: Brain, blue: true },
  ];

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
      className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">System Infrastructure</p>
      <div className="space-y-2.5">
        {statuses.map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">{s.label}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {(s as { blue?: boolean }).blue ? (
                  <Pulse color="bg-blue-500" />
                ) : s.ok ? (
                  <Pulse color="bg-emerald-500" />
                ) : (
                  <Pulse color="bg-red-500" />
                )}
                <span className={cn("text-xs font-medium",
                  (s as { blue?: boolean }).blue ? "text-blue-500" : s.ok ? "text-emerald-500" : "text-red-500"
                )}>
                  {s.detail}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

// ── Academic Health Chart ─────────────────────────────────────────────────────
function AcademicHealthChart({ analytics }: { analytics: ReturnType<typeof getPlatformAnalytics> extends Promise<infer T> ? T : never }) {
  const bars = [
    { name: "Assignments", value: analytics.total_assignments, fill: "#6366f1" },
    { name: "Quizzes", value: analytics.total_quizzes, fill: "#06b6d4" },
    { name: "Students", value: analytics.total_students, fill: "#8b5cf6" },
    { name: "Staff", value: analytics.total_staff, fill: "#10b981" },
    { name: "Classes", value: analytics.total_classrooms, fill: "#f59e0b" },
  ];
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}
      className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/15">
          <BarChart3 className="h-4 w-4 text-indigo-500" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">Academic Health</p>
          <p className="text-xs text-muted-foreground">Platform resource counts</p>
        </div>
      </div>
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bars} margin={{ top: 4, right: 0, bottom: 0, left: -20 }} barSize={28}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
              cursor={{ fill: "hsl(var(--muted))" }}
            />
            {bars.map((b) => (
              <Bar key={b.name} dataKey="value" fill={b.fill} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

// ── Error Boundary Widget ─────────────────────────────────────────────────────
function APIErrorWidget({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-border p-10 text-center">
      <AlertTriangle className="h-8 w-8 text-amber-500" />
      <p className="font-medium text-foreground">Could not load analytics</p>
      <p className="text-sm text-muted-foreground">The backend may be starting up or unreachable.</p>
      <button onClick={onRetry}
        className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent">
        <Wifi className="h-4 w-4" />
        Sync with API
      </button>
    </div>
  );
}

// ── Live Activity feed ────────────────────────────────────────────────────────
type FeedItem = { id: number; msg: string; ts: Date };
function useLiveFeed() {
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const idRef = useRef(0);
  // Expose so WS hook can push items
  const push = (msg: string) =>
    setFeed((prev) => [{ id: ++idRef.current, msg, ts: new Date() }, ...prev.slice(0, 6)]);
  return { feed, push };
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function AdminDashboard() {
  const user = useAuthStore((s) => s.user);
  const { data: analytics, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.analytics.platform(),
    queryFn: getPlatformAnalytics,
    staleTime: 60_000,
    retry: 2,
  });
  const { feed } = useLiveFeed();

  // Stable sparklines (don't regenerate on re-renders)
  const [sparks] = useState({
    users: mkSparkline(analytics?.total_users ?? 80),
    students: mkSparkline(analytics?.total_students ?? 60),
    staff: mkSparkline(analytics?.total_staff ?? 10),
    rooms: mkSparkline(analytics?.total_classrooms ?? 5),
  });

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                {greeting}, {user?.first_name ?? "Admin"} 👋
              </h1>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Here's what's happening across your platform today.
              </p>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">All systems operational</span>
            </div>
          </div>
        </motion.div>

        {isLoading && (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-36 animate-pulse rounded-2xl bg-muted" />
            ))}
          </div>
        )}

        {isError && <APIErrorWidget onRetry={() => refetch()} />}

        {analytics && (
          <>
            {/* KPI Grid */}
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <KPICard label="Total Users" value={analytics.total_users}
                icon={Users} color="text-blue-500" bgColor="bg-blue-500/15"
                trend="Platform total" sparkData={sparks.users} delay={0} href="/admin/users" />
              <KPICard label="Students" value={analytics.total_students}
                icon={GraduationCap} color="text-purple-500" bgColor="bg-purple-500/15"
                trend="Enrolled" sparkData={sparks.students} delay={0.06} href="/admin/students" />
              <KPICard label="Staff" value={analytics.total_staff}
                icon={UserCheck} color="text-emerald-500" bgColor="bg-emerald-500/15"
                trend="Active teachers" sparkData={sparks.staff} delay={0.12} href="/admin/staff" />
              <KPICard label="Classrooms" value={analytics.total_classrooms}
                icon={School} color="text-orange-500" bgColor="bg-orange-500/15"
                trend="Active rooms" sparkData={sparks.rooms} delay={0.18} href="/admin/academic" />
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <KPICard label="Assignments" value={analytics.total_assignments}
                icon={ClipboardList} color="text-pink-500" bgColor="bg-pink-500/15"
                delay={0.24} />
              <KPICard label="Subjects" value={analytics.total_subjects ?? 0}
                icon={BookOpen} color="text-violet-500" bgColor="bg-violet-500/15"
                trend="Active subjects" delay={0.28} href="/admin/subjects" />
              <KPICard label="Quizzes" value={analytics.total_quizzes}
                icon={BookOpen} color="text-cyan-500" bgColor="bg-cyan-500/15"
                delay={0.3} />
              <KPICard label="Submissions Today" value={analytics.submissions_today}
                icon={TrendingUp} color="text-indigo-500" bgColor="bg-indigo-500/15"
                delay={0.36} />
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <KPICard label="Active Sessions" value={analytics.active_sessions}
                icon={Activity} color="text-amber-500" bgColor="bg-amber-500/15"
                delay={0.42} />
            </div>

            {/* AI + Staff Load + System row */}
            <div className="grid gap-4 lg:grid-cols-3">
              <AIQueueBadge initialCount={analytics.grading_queue} />
              <StaffLoadBar students={analytics.total_students} staff={analytics.total_staff} />
              <SystemStatus />
            </div>

            {/* Academic Health Chart + Live Feed */}
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <AcademicHealthChart analytics={analytics} />
              </div>

              {/* Live Activity */}
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 }}
                className="rounded-2xl border border-border bg-card p-5 shadow-sm">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Live Activity</p>
                {feed.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <Pulse color="bg-muted-foreground" />
                    <p className="mt-3 text-xs text-muted-foreground">Waiting for events…</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <AnimatePresence initial={false}>
                      {feed.map((f) => (
                        <motion.div key={f.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, height: 0 }}
                          className="flex items-start gap-2 rounded-lg bg-muted/50 px-3 py-2 text-xs">
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
                          <div>
                            <p className="text-foreground">{f.msg}</p>
                            <p className="text-muted-foreground">{f.ts.toLocaleTimeString()}</p>
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </motion.div>
            </div>

            {/* Quick actions */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
              className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {[
                { label: "Add User", href: "/admin/users", icon: Users, color: "text-blue-500", bg: "bg-blue-500/10" },
                { label: "Add Student", href: "/admin/students", icon: GraduationCap, color: "text-purple-500", bg: "bg-purple-500/10" },
                { label: "Add Staff", href: "/admin/staff", icon: UserCheck, color: "text-emerald-500", bg: "bg-emerald-500/10" },
                { label: "Subjects", href: "/admin/subjects", icon: BookOpen, color: "text-violet-500", bg: "bg-violet-500/10" },
                { label: "Timetable", href: "/admin/timetable", icon: ClipboardList, color: "text-orange-500", bg: "bg-orange-500/10" },
                { label: "Analytics", href: "/admin/analytics", icon: BarChart3, color: "text-indigo-500", bg: "bg-indigo-500/10" },
              ].map((a) => (
                <Link key={a.href} href={a.href}
                  className="group flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium text-foreground transition-all hover:border-primary/40 hover:shadow-sm">
                  <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg transition-transform group-hover:scale-110", a.bg)}>
                    <a.icon className={cn("h-4 w-4", a.color)} />
                  </div>
                  {a.label}
                  <ChevronRight className="ml-auto h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                </Link>
              ))}
            </motion.div>
          </>
        )}
      </div>
    </AuthGuard>
  );
}

