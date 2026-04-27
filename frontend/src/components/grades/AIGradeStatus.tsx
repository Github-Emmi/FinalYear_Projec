"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export type GradeStatus = "pending" | "graded" | "not_submitted";

interface AIGradeStatusProps {
  status: GradeStatus;
  score?: number | null;
  maxScore?: number | null;
  aiFeedback?: string | null;
  className?: string;
}

/**
 * Displays the AI grading status of a submission or quiz attempt.
 * - pending → spinning loader badge
 * - graded → animated score reveal with optional AI feedback
 * - not_submitted → neutral badge
 */
export function AIGradeStatus({
  status,
  score,
  maxScore,
  aiFeedback,
  className,
}: AIGradeStatusProps) {
  const percentage =
    score !== null && score !== undefined && maxScore
      ? Math.round((score / maxScore) * 100)
      : null;

  const scoreColor =
    percentage === null
      ? "text-muted-foreground"
      : percentage >= 70
      ? "text-green-600 dark:text-green-400"
      : percentage >= 50
      ? "text-yellow-600 dark:text-yellow-400"
      : "text-red-600 dark:text-red-400";

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {/* Status badge */}
      <div className="flex items-center gap-2">
        {status === "pending" && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-sm font-medium text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Grading…
          </span>
        )}

        {status === "not_submitted" && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-sm font-medium text-muted-foreground">
            <XCircle className="h-3.5 w-3.5" />
            Not submitted
          </span>
        )}

        {status === "graded" && (
          <AnimatePresence>
            <motion.div
              key="score"
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 24 }}
              className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-sm font-medium"
            >
              <CheckCircle className="h-3.5 w-3.5 text-green-500" />
              <span className={scoreColor}>
                {score !== null && score !== undefined ? (
                  <>
                    <strong>{score}</strong>
                    {maxScore ? `/${maxScore}` : ""}
                    {percentage !== null && (
                      <span className="ml-1 text-xs text-muted-foreground">
                        ({percentage}%)
                      </span>
                    )}
                  </>
                ) : (
                  "Graded"
                )}
              </span>
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* AI feedback (graded state only) */}
      {status === "graded" && aiFeedback && (
        <AnimatePresence>
          <motion.div
            key="feedback"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 0.15, duration: 0.3 }}
            className="rounded-lg border border-border bg-muted/50 p-3 text-sm text-muted-foreground"
          >
            <p className="mb-1 font-semibold text-foreground">AI Feedback</p>
            <p className="whitespace-pre-wrap leading-relaxed">{aiFeedback}</p>
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
