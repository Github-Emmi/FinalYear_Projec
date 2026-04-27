"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Calendar, Loader2, CheckCircle, XCircle } from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import { getPendingLeaveRequests, approveLeaveRequest, rejectLeaveRequest } from "@/lib/api/leave";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { formatDate } from "@/lib/utils/dates";
import { toast } from "sonner";

export default function AdminLeavePage() {
  const queryClient = useQueryClient();

  const { data: pending, isLoading } = useQuery({
    queryKey: queryKeys.leave.pending(),
    queryFn: getPendingLeaveRequests,
  });

  const approveMutation = useMutation({
    mutationFn: approveLeaveRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave"] });
      toast.success("Leave request approved");
    },
    onError: () => toast.error("Failed to approve"),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectLeaveRequest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave"] });
      toast.success("Leave request rejected");
    },
    onError: () => toast.error("Failed to reject"),
  });

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Leave Requests</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Review and respond to pending leave requests
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {(!pending || pending.length === 0) && (
              <div className="rounded-xl border border-border bg-card py-12 text-center">
                <Calendar className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                <p className="text-muted-foreground">No pending leave requests</p>
              </div>
            )}
            {pending?.map((l) => (
              <motion.div
                key={l.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl border border-border bg-card p-5 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-foreground">{l.leave_type}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {formatDate(l.start_date)} – {formatDate(l.end_date)}
                    </p>
                    {l.reason && (
                      <p className="mt-2 text-sm text-foreground">{l.reason}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => approveMutation.mutate(l.id)}
                      disabled={approveMutation.isPending}
                      className="flex items-center gap-1.5 rounded-lg bg-green-500 px-3 py-1.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
                    >
                      <CheckCircle className="h-4 w-4" />
                      Approve
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(l.id)}
                      disabled={rejectMutation.isPending}
                      className="flex items-center gap-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
                    >
                      <XCircle className="h-4 w-4" />
                      Reject
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
