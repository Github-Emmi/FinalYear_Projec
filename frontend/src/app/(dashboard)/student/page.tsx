"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ClipboardList, BookOpen, UserCheck, Loader2 } from "lucide-react";
import Link from "next/link";
import { queryKeys } from "@/lib/query/keys";
import { listAssignments } from "@/lib/api/assignments";
import { getMyStudentProfile, getStudentAnalytics } from "@/lib/api/students";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { AIGradeStatus } from "@/components/grades/AIGradeStatus";
import { formatDate } from "@/lib/utils/dates";
import { cn } from "@/lib/utils/cn";

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className={cn("h-full rounded-full", color)}
      />
    </div>
  );
}

export default function StudentDashboard() {
  const { data: profile } = useQuery({
    queryKey: queryKeys.students.me(),
    queryFn: getMyStudentProfile,
    retry: false,
  });

  const { data: analytics } = useQuery({
    queryKey: profile?.id ? queryKeys.students.analytics(profile.id) : ["noop"],
    queryFn: () => getStudentAnalytics(profile!.id),
    enabled: !!profile?.id,
  });

  const { data: assignments, isLoading: loadingAssignments } = useQuery({
    queryKey: queryKeys.assignments.all({ page: 1, size: 5, status: "published" }),
    queryFn: () => listAssignments({ page: 1, size: 5, status: "published" }),
  });

  return (
    <AuthGuard allowedRoles={["student"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Student Dashboard
          </h1>
          {profile && (
            <p className="mt-1 text-sm text-muted-foreground">
              Welcome back,{" "}
              <span className="font-medium">
                {profile.user?.first_name} {profile.user?.last_name}
              </span>{" "}
              · {profile.classroom?.name}
            </p>
          )}
        </div>

        {/* Analytics cards */}
        {analytics && (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              {
                label: "Attendance Rate",
                value: Math.round(analytics.attendance_rate),
                color: "bg-emerald-500",
                icon: UserCheck,
              },
              {
                label: "Assignment Score",
                value: Math.round(analytics.average_score),
                color: "bg-blue-500",
                icon: ClipboardList,
              },
              {
                label: "Quiz Average",
                value: Math.round(analytics.quiz_average),
                color: "bg-purple-500",
                icon: BookOpen,
              },
              {
                label: "Completion Rate",
                value: Math.round(analytics.assignment_completion_rate),
                color: "bg-orange-500",
                icon: ClipboardList,
              },
            ].map((stat, i) => {
              const Icon = stat.icon;
              return (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.3 }}
                  className="rounded-xl border border-border bg-card p-5 shadow-sm"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <Icon className={cn("h-4 w-4 text-white rounded-md p-0.5", stat.color)} />
                  </div>
                  <p className="mb-2 text-2xl font-bold text-foreground">
                    {stat.value}%
                  </p>
                  <ProgressBar value={stat.value} color={stat.color} />
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Active assignments */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.3 }}
          className="rounded-xl border border-border bg-card p-5 shadow-sm"
        >
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-primary" />
              <h2 className="font-semibold text-foreground">
                Active Assignments
              </h2>
            </div>
            <Link
              href="/student/assignments"
              className="text-xs text-primary hover:underline"
            >
              View all
            </Link>
          </div>

          {loadingAssignments ? (
            <div className="flex justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <ul className="space-y-3">
              {assignments?.items.length === 0 && (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No active assignments
                </p>
              )}
              {assignments?.items.map((a) => (
                <li key={a.id}>
                  <Link
                    href={`/student/assignments/${a.id}`}
                    className="flex items-center justify-between rounded-lg p-2 transition-colors hover:bg-accent"
                  >
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {a.title}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Due {formatDate(a.due_date)} · Max score: {a.max_score}
                      </p>
                    </div>
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                      {a.status}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </motion.div>
      </div>
    </AuthGuard>
  );
}
