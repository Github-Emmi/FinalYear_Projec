"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ClipboardList,
  BookOpen,
  Loader2,
  Calendar,
  Users,
  TrendingUp,
} from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import { listAssignments } from "@/lib/api/assignments";
import { listLeaveRequests } from "@/lib/api/leave";
import { getMyStaffProfile } from "@/lib/api/staff";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { formatDate, formatRelative } from "@/lib/utils/dates";
import { cn } from "@/lib/utils/cn";
import Link from "next/link";

export default function StaffDashboard() {
  const { data: staffProfile } = useQuery({
    queryKey: queryKeys.staff.detail("me"),
    queryFn: getMyStaffProfile,
    retry: false,
  });

  const { data: assignments, isLoading: loadingAssignments } = useQuery({
    queryKey: queryKeys.assignments.all({ page: 1, size: 5 }),
    queryFn: () => listAssignments({ page: 1, size: 5 }),
  });

  const { data: leaveRequests, isLoading: loadingLeave } = useQuery({
    queryKey: queryKeys.leave.all({ page: 1, size: 5 }),
    queryFn: () => listLeaveRequests({ page: 1, size: 5 }),
  });

  return (
    <AuthGuard allowedRoles={["staff"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Staff Dashboard
          </h1>
          {staffProfile && (
            <p className="mt-1 text-sm text-muted-foreground">
              Welcome back,{" "}
              <span className="font-medium">
                {staffProfile.user?.first_name} {staffProfile.user?.last_name}
              </span>{" "}
              · {staffProfile.designation ?? "Staff Member"}
            </p>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Recent Assignments */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-xl border border-border bg-card p-5 shadow-sm"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ClipboardList className="h-5 w-5 text-primary" />
                <h2 className="font-semibold text-foreground">
                  Recent Assignments
                </h2>
              </div>
              <Link
                href="/staff/assignments"
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
                    No assignments yet
                  </p>
                )}
                {assignments?.items.map((a) => (
                  <li key={a.id}>
                    <Link
                      href={`/staff/assignments/${a.id}`}
                      className="flex items-center justify-between rounded-lg p-2 transition-colors hover:bg-accent"
                    >
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {a.title}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Due {formatDate(a.due_date)}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-medium",
                          a.status === "published"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : a.status === "closed"
                            ? "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
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
          </motion.div>

          {/* Leave Requests */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.3 }}
            className="rounded-xl border border-border bg-card p-5 shadow-sm"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-primary" />
                <h2 className="font-semibold text-foreground">
                  Leave Requests
                </h2>
              </div>
              <Link
                href="/staff/leave"
                className="text-xs text-primary hover:underline"
              >
                View all
              </Link>
            </div>

            {loadingLeave ? (
              <div className="flex justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <ul className="space-y-3">
                {leaveRequests?.items.length === 0 && (
                  <p className="py-4 text-center text-sm text-muted-foreground">
                    No leave requests
                  </p>
                )}
                {leaveRequests?.items.map((l) => (
                  <li key={l.id} className="flex items-center justify-between rounded-lg p-2">
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
                        "rounded-full px-2 py-0.5 text-xs font-medium",
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
          </motion.div>
        </div>
      </div>
    </AuthGuard>
  );
}
