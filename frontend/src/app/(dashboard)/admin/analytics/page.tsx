"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BarChart2, Loader2 } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
} from "recharts";
import { queryKeys } from "@/lib/query/keys";
import { getPlatformAnalytics } from "@/lib/api/analytics";
import { listClassrooms } from "@/lib/api/academic";
import { getClassroomAnalytics } from "@/lib/api/analytics";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function AdminAnalyticsPage() {
  const [selectedClassroom, setSelectedClassroom] = useState<string>("");

  const { data: platform, isLoading: loadingPlatform } = useQuery({
    queryKey: queryKeys.analytics.platform(),
    queryFn: getPlatformAnalytics,
  });

  const { data: classrooms } = useQuery({
    queryKey: queryKeys.academic.classrooms(),
    queryFn: () => listClassrooms({ size: 50 }),
  });

  const { data: classroomAnalytics, isLoading: loadingClassroom } = useQuery({
    queryKey: selectedClassroom
      ? queryKeys.analytics.classroom(selectedClassroom)
      : ["noop"],
    queryFn: () => getClassroomAnalytics(selectedClassroom),
    enabled: !!selectedClassroom,
  });

  const platformChartData = platform
    ? [
        { name: "Students", value: platform.total_students },
        { name: "Staff", value: platform.total_staff },
        { name: "Classrooms", value: platform.total_classrooms },
        { name: "Assignments", value: platform.total_assignments },
        { name: "Quizzes", value: platform.total_quizzes },
      ]
    : [];

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Analytics</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Platform-wide metrics and classroom insights
          </p>
        </div>

        {/* Platform overview chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-border bg-card p-5 shadow-sm"
        >
          <h2 className="mb-4 font-semibold text-foreground">
            Platform Overview
          </h2>
          {loadingPlatform ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={platformChartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12 }}
                  className="text-muted-foreground"
                />
                <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar
                  dataKey="value"
                  fill="hsl(var(--primary))"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Classroom drill-down */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl border border-border bg-card p-5 shadow-sm"
        >
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="font-semibold text-foreground">
              Classroom Analytics
            </h2>
            <select
              value={selectedClassroom}
              onChange={(e) => setSelectedClassroom(e.target.value)}
              className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select a classroom…</option>
              {classrooms?.items?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {!selectedClassroom && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Select a classroom to view analytics
            </p>
          )}

          {loadingClassroom && selectedClassroom && (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {classroomAnalytics && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                  {
                    label: "Students",
                    value: classroomAnalytics.total_students,
                  },
                  {
                    label: "Avg Attendance",
                    value: `${Math.round(classroomAnalytics.average_attendance)}%`,
                  },
                  {
                    label: "Avg Assignment Score",
                    value: `${Math.round(classroomAnalytics.average_assignment_score)}%`,
                  },
                  {
                    label: "Completion Rate",
                    value: `${Math.round(classroomAnalytics.assignment_completion_rate)}%`,
                  },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-lg bg-muted/50 p-3 text-center"
                  >
                    <p className="text-xs text-muted-foreground">
                      {stat.label}
                    </p>
                    <p className="mt-1 text-xl font-bold text-foreground">
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>

              {(classroomAnalytics.recent_activity ?? []).length > 0 && (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={classroomAnalytics.recent_activity ?? []}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        borderColor: "hsl(var(--border))",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </AuthGuard>
  );
}
