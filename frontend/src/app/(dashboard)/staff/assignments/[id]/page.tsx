"use client";

import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { queryKeys } from "@/lib/query/keys";
import { getAssignment, listSubmissions, triggerAIGrading } from "@/lib/api/assignments";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { AIGradeStatus } from "@/components/grades/AIGradeStatus";
import { formatDate, formatRelative } from "@/lib/utils/dates";
import { toast } from "sonner";

interface Params {
  id: string;
}

export default function AssignmentDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = use(params);
  const queryClient = useQueryClient();

  const { data: assignment, isLoading: loadingAssignment } = useQuery({
    queryKey: queryKeys.assignments.detail(id),
    queryFn: () => getAssignment(id),
  });

  const { data: submissions, isLoading: loadingSubmissions } = useQuery({
    queryKey: queryKeys.assignments.submissions(id),
    queryFn: () => listSubmissions(id),
    enabled: !!id,
  });

  const gradeMutation = useMutation({
    mutationFn: triggerAIGrading,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.assignments.submissions(id),
      });
      toast.success("AI grading queued");
    },
    onError: () => {
      toast.error("Failed to queue grading");
    },
  });

  if (loadingAssignment) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <AuthGuard allowedRoles={["staff"]}>
      <div className="space-y-6">
        <div className="flex items-start gap-4">
          <Link
            href="/staff/assignments"
            className="mt-1 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              {assignment?.title}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Due {assignment ? formatDate(assignment.due_date) : "…"} · Max
              score: {assignment?.max_score}
            </p>
          </div>
        </div>

        {assignment?.description && (
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-sm text-foreground">{assignment.description}</p>
          </div>
        )}

        {/* Submissions */}
        <div>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            Submissions ({submissions?.length ?? 0})
          </h2>

          {loadingSubmissions ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-3">
              {(!submissions || submissions.length === 0) && (
                <p className="rounded-xl border border-border bg-card py-8 text-center text-sm text-muted-foreground">
                  No submissions yet
                </p>
              )}
              {submissions?.map((sub) => (
                <motion.div
                  key={sub.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-border bg-card p-4"
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        Student: {sub.student_id}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Submitted {formatRelative(sub.submitted_at)}
                        {sub.is_late && (
                          <span className="ml-2 rounded-full bg-orange-100 px-1.5 py-0.5 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
                            Late
                          </span>
                        )}
                      </p>
                    </div>

                    {sub.grade_status !== "graded" && (
                      <button
                        onClick={() => gradeMutation.mutate(sub.id)}
                        disabled={gradeMutation.isPending}
                        className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
                      >
                        {gradeMutation.isPending ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Sparkles className="h-3 w-3" />
                        )}
                        Grade with AI
                      </button>
                    )}
                  </div>

                  <p className="mb-3 rounded-lg bg-muted/50 p-3 text-sm text-foreground">
                    {sub.content}
                  </p>

                  <AIGradeStatus
                    status={sub.grade_status}
                    score={sub.score}
                    maxScore={sub.max_score}
                    aiFeedback={sub.ai_feedback}
                  />
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}
