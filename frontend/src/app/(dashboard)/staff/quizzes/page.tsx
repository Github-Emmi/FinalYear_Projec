"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BookOpen, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { queryKeys } from "@/lib/query/keys";
import { listQuizzes } from "@/lib/api/assessments";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function StaffQuizzesPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.quizzes.all({ page, size: 10 }),
    queryFn: () => listQuizzes({ page, size: 10 }),
  });

  return (
    <AuthGuard allowedRoles={["staff"]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Quizzes</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Create and manage quizzes
            </p>
          </div>
          <Link
            href="/staff/quizzes/new"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            + New Quiz
          </Link>
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
                <p className="text-muted-foreground">No quizzes yet</p>
              </div>
            )}
            {data?.items.map((q) => (
              <motion.div
                key={q.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl border border-border bg-card p-5 shadow-sm"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-foreground">{q.title}</h3>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                      q.is_published
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                    }`}
                  >
                    {q.is_published ? "Published" : "Draft"}
                  </span>
                </div>
                {q.description && (
                  <p className="mb-3 text-xs text-muted-foreground line-clamp-2">
                    {q.description}
                  </p>
                )}
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Max attempts: {q.max_attempts}</span>
                  {q.time_limit_minutes && (
                    <span>{q.time_limit_minutes} min</span>
                  )}
                </div>
                <Link
                  href={`/staff/quizzes/${q.id}`}
                  className="mt-3 block w-full rounded-lg bg-muted px-3 py-2 text-center text-xs font-medium text-foreground transition-colors hover:bg-accent"
                >
                  View details
                </Link>
              </motion.div>
            ))}
          </div>
        )}

        {data && data.pages > 1 && (
          <div className="flex justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg px-3 py-1.5 text-xs font-medium hover:bg-accent disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
              disabled={page === data.pages}
              className="rounded-lg px-3 py-1.5 text-xs font-medium hover:bg-accent disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
