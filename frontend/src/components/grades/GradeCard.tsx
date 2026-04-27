"use client";

import { formatDate, formatRelative } from "@/lib/utils/dates";
import { AIGradeStatus } from "./AIGradeStatus";
import type { SubmissionResponse } from "@/types/models";
import { cn } from "@/lib/utils/cn";

interface GradeCardProps {
  submission: SubmissionResponse;
  className?: string;
}

export function GradeCard({ submission, className }: GradeCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-4 shadow-sm",
        className
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">
          Submitted {formatRelative(submission.submitted_at)}
        </p>
        {submission.is_late && (
          <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
            Late
          </span>
        )}
      </div>

      <AIGradeStatus
        status={submission.grade_status}
        score={submission.score}
        maxScore={submission.max_score}
        aiFeedback={submission.ai_feedback}
      />

      {submission.graded_at && (
        <p className="mt-2 text-xs text-muted-foreground">
          Graded on {formatDate(submission.graded_at)}
        </p>
      )}
    </div>
  );
}
