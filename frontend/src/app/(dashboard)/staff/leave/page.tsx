"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import { listLeaveRequests, createLeaveRequest } from "@/lib/api/leave";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { leaveRequestSchema, type LeaveRequestInput } from "@/lib/schemas/leave.schema";
import { formatDate } from "@/lib/utils/dates";
import { cn } from "@/lib/utils/cn";
import { toast } from "sonner";

export default function StaffLeavePage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.leave.all({ page: 1, size: 20 }),
    queryFn: () => listLeaveRequests({ page: 1, size: 20 }),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LeaveRequestInput>({
    resolver: zodResolver(leaveRequestSchema),
  });

  const createMutation = useMutation({
    mutationFn: createLeaveRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave"] });
      reset();
      setShowForm(false);
      toast.success("Leave request submitted");
    },
    onError: () => toast.error("Failed to submit leave request"),
  });

  const onSubmit = (data: LeaveRequestInput) => createMutation.mutate(data);

  return (
    <AuthGuard allowedRoles={["staff"]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Leave</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Submit and track your leave requests
            </p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            Request Leave
          </button>
        </div>

        {/* New request form */}
        {showForm && (
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="rounded-xl border border-border bg-card p-5 shadow-sm"
          >
            <h2 className="mb-4 font-semibold text-foreground">
              New Leave Request
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">
                  Leave Type
                </label>
                <select
                  {...register("leave_type")}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">Select type…</option>
                  <option value="Annual">Annual</option>
                  <option value="Sick">Sick</option>
                  <option value="Maternity">Maternity</option>
                  <option value="Paternity">Paternity</option>
                  <option value="Unpaid">Unpaid</option>
                  <option value="Other">Other</option>
                </select>
                {errors.leave_type && (
                  <p className="text-xs text-destructive">
                    {errors.leave_type.message}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">
                  Start Date
                </label>
                <input
                  type="date"
                  {...register("start_date")}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
                {errors.start_date && (
                  <p className="text-xs text-destructive">
                    {errors.start_date.message}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">
                  End Date
                </label>
                <input
                  type="date"
                  {...register("end_date")}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
                {errors.end_date && (
                  <p className="text-xs text-destructive">
                    {errors.end_date.message}
                  </p>
                )}
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-sm font-medium text-foreground">
                  Reason
                </label>
                <textarea
                  {...register("reason")}
                  rows={3}
                  placeholder="Describe the reason for your leave…"
                  className="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
                {errors.reason && (
                  <p className="text-xs text-destructive">
                    {errors.reason.message}
                  </p>
                )}
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  reset();
                  setShowForm(false);
                }}
                className="rounded-lg px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
              >
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                Submit
              </button>
            </div>
          </form>
        )}

        {/* Leave history */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {(!data?.items || data.items.length === 0) && (
              <p className="rounded-xl border border-border bg-card py-8 text-center text-sm text-muted-foreground">
                No leave requests yet
              </p>
            )}
            {data?.items.map((l) => (
              <div
                key={l.id}
                className="flex items-center justify-between rounded-xl border border-border bg-card px-5 py-4"
              >
                <div>
                  <p className="font-medium text-foreground">{l.leave_type}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(l.start_date)} – {formatDate(l.end_date)}
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                    l.status === "approved"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : l.status === "rejected"
                      ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                  )}
                >
                  {l.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
