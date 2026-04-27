"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BookOpen, Loader2, Clock } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { queryKeys } from "@/lib/query/keys";
import { listQuizzes, getMyAttempts } from "@/lib/api/assessments";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { AIGradeStatus } from "@/components/grades/AIGradeStatus";

export default function StudentQuizzesPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.quizzes.all({ page, size: 10, is_published: true }),
    queryFn: () => listQuizzes({ page, size: 10, is_published: true }),
  });

  const { data: myAttempts } = useQuery({
    queryKey: queryKeys.quizzes.myAttempts(),
    queryFn: getMyAttempts,
  });

  // Map quizId -> attempt
  const attemptByQuiz = Object.fromEntries(
    (myAttempts ?? []).map((a) => [a.quiz_id, a])
  );

  return (
    <AuthGuard allowedRoles={["student"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Quizzes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Take quizzes and view your results
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data?.items.length === 0 && (
              <div className="col-span-full rounded-xl border border-border bg-card py-12 text-center">
                <BookOpen className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                <p className="text-muted-foreground">No quizzes available</p>
              </div>
            )}
            {data?.items.map((q) => {
              const attempt = attemptByQuiz[q.id];

              return (
                <motion.div
                  key={q.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col rounded-xl border border-border bg-card p-5 shadow-sm"
                >
                  <h3 className="mb-1 font-semibold text-foreground">
                    {q.title}
                  </h3>
                  {q.description && (
                    <p className="mb-3 text-xs text-muted-foreground line-clamp-2">
                      {q.description}
                    </p>
                  )}
                  <div className="mb-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>Max attempts: {q.max_attempts}</span>
                    {q.time_limit_minutes && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {q.time_limit_minutes} min
                      </span>
                    )}
                  </div>

                  {attempt ? (
                    <div className="mt-auto">
                      <AIGradeStatus
                        status={attempt.grade_status}
                        score={attempt.score}
                        maxScore={attempt.max_score}
                        aiFeedback={attempt.ai_feedback}
                      />
                    </div>
                  ) : (
                    <Link
                      href={`/student/quizzes/${q.id}`}
                      className="mt-auto block w-full rounded-lg bg-primary px-3 py-2 text-center text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
                    >
                      Start Quiz
                    </Link>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
