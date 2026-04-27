"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  ClipboardList,
  Loader2,
  Send,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import Link from "next/link";
import { queryKeys } from "@/lib/query/keys";
import { listAssignments, submitAssignment, getSubmission } from "@/lib/api/assignments";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { AIGradeStatus } from "@/components/grades/AIGradeStatus";
import { formatDate } from "@/lib/utils/dates";
import { toast } from "sonner";

export default function StudentAssignmentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [submissionTexts, setSubmissionTexts] = useState<
    Record<string, string>
  >({});

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.assignments.all({ page, size: 10, status: "published" }),
    queryFn: () => listAssignments({ page, size: 10, status: "published" }),
  });

  const submitMutation = useMutation({
    mutationFn: ({
      assignmentId,
      content,
    }: {
      assignmentId: string;
      content: string;
    }) => submitAssignment(assignmentId, content),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["assignments"] });
      setSubmissionTexts((prev) => ({ ...prev, [variables.assignmentId]: "" }));
      toast.success("Assignment submitted! AI grading in progress…");
    },
    onError: () => {
      toast.error("Failed to submit assignment");
    },
  });

  return (
    <AuthGuard allowedRoles={["student"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Assignments</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            View and submit your assignments
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {data?.items.length === 0 && (
              <div className="rounded-xl border border-border bg-card py-12 text-center">
                <ClipboardList className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                <p className="text-muted-foreground">
                  No assignments available
                </p>
              </div>
            )}

            {data?.items.map((a) => {
              const isExpanded = expandedId === a.id;
              const text = submissionTexts[a.id] ?? "";

              return (
                <motion.div
                  key={a.id}
                  layout
                  className="overflow-hidden rounded-xl border border-border bg-card shadow-sm"
                >
                  {/* Header */}
                  <button
                    onClick={() =>
                      setExpandedId(isExpanded ? null : a.id)
                    }
                    className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-accent/50"
                  >
                    <div>
                      <p className="font-semibold text-foreground">{a.title}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        Due {formatDate(a.due_date)} · Max score: {a.max_score}
                      </p>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>

                  {/* Expanded body */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        key="body"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="border-t border-border px-5 pb-5 pt-4"
                      >
                        {a.description && (
                          <p className="mb-4 text-sm text-muted-foreground">
                            {a.description}
                          </p>
                        )}

                        <textarea
                          value={text}
                          onChange={(e) =>
                            setSubmissionTexts((prev) => ({
                              ...prev,
                              [a.id]: e.target.value,
                            }))
                          }
                          rows={5}
                          placeholder="Write your answer here…"
                          className="w-full resize-y rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />

                        <div className="mt-3 flex justify-end">
                          <button
                            onClick={() => {
                              if (!text.trim()) {
                                toast.error(
                                  "Please write something before submitting"
                                );
                                return;
                              }
                              submitMutation.mutate({
                                assignmentId: a.id,
                                content: text,
                              });
                            }}
                            disabled={
                              submitMutation.isPending || !text.trim()
                            }
                            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {submitMutation.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Send className="h-4 w-4" />
                            )}
                            Submit
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}

            {/* Pagination */}
            {data && data.pages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-muted-foreground">
                  Page {data.page} of {data.pages}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                    disabled={page === data.pages}
                    className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
