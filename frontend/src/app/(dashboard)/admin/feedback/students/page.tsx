"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  GraduationCap,
  Loader2,
  MessageSquare,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import {
  listFeedbackThreads,
  type FeedbackThreadResponse,
} from "@/lib/api/feedback";
import { FeedbackChatPanel } from "@/components/feedback/FeedbackChatPanel";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { cn } from "@/lib/utils/cn";
import { formatDistanceToNow } from "date-fns";

// ── Thread list item ──────────────────────────────────────────────────────────

function ThreadItem({
  thread,
  active,
  onClick,
}: {
  thread: FeedbackThreadResponse;
  active: boolean;
  onClick: () => void;
}) {
  const senderName = thread.sender
    ? `${thread.sender.first_name ?? ""} ${thread.sender.last_name ?? ""}`.trim() ||
      thread.sender.email
    : "Unknown";

  const initials = thread.sender
    ? (
        (thread.sender.first_name?.[0] ?? "") +
        (thread.sender.last_name?.[0] ?? "")
      ).toUpperCase() || thread.sender.email[0].toUpperCase()
    : "?";

  const lastMsg = thread.last_message;
  const hasUnread = thread.unread_by_admin > 0;

  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-start gap-3 rounded-xl px-3 py-3 text-left transition-all",
        active
          ? "bg-primary/10 ring-1 ring-primary/30"
          : "hover:bg-accent",
        hasUnread && !active && "border-l-2 border-primary"
      )}
    >
      {/* Avatar */}
      <div className="relative flex-shrink-0">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 text-sm font-bold text-white">
          {initials}
        </div>
        {hasUnread && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground">
            {thread.unread_by_admin}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-1">
          <p className={cn("truncate text-sm", hasUnread ? "font-semibold text-foreground" : "font-medium text-foreground")}>
            {senderName}
          </p>
          <p className="shrink-0 text-[10px] text-muted-foreground">
            {formatDistanceToNow(new Date(thread.updated_at), { addSuffix: true })}
          </p>
        </div>
        {thread.subject && (
          <p className="truncate text-xs font-medium text-muted-foreground">
            {thread.subject}
          </p>
        )}
        {lastMsg && (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {lastMsg.is_admin_message ? "You: " : ""}
            {lastMsg.body}
          </p>
        )}
      </div>

      {/* Status badge */}
      <span
        className={cn(
          "mt-0.5 shrink-0 self-start rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
          thread.status === "resolved"
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
            : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
        )}
      >
        {thread.status}
      </span>
    </button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminStudentFeedbackPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | "open" | "resolved">("");

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.feedback.threads({ role_filter: "student", status: statusFilter || undefined }),
    queryFn: () =>
      listFeedbackThreads({
        role_filter: "student",
        status: statusFilter as "open" | "resolved" | undefined || undefined,
        size: 50,
      }),
    refetchInterval: 15_000,
  });

  const threads = (data?.items ?? []).filter((t) => {
    if (!search) return true;
    const s = search.toLowerCase();
    const name = t.sender
      ? `${t.sender.first_name ?? ""} ${t.sender.last_name ?? ""} ${t.sender.email}`.toLowerCase()
      : "";
    return name.includes(s) || (t.subject ?? "").toLowerCase().includes(s);
  });

  const selectedThread = threads.find((t) => t.id === selectedId) ?? null;

  const totalUnread = (data?.items ?? []).reduce((n, t) => n + t.unread_by_admin, 0);

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="flex h-[calc(100vh-7rem)] gap-4 overflow-hidden">
        {/* ── Thread sidebar ─────────────────────────────────────────────── */}
        <div className="flex w-80 shrink-0 flex-col rounded-2xl border border-border bg-card shadow-sm">
          {/* Header */}
          <div className="border-b border-border px-4 py-4">
            <div className="flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-primary" />
              <h1 className="font-semibold text-foreground">Student Feedback</h1>
              {totalUnread > 0 && (
                <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground">
                  {totalUnread}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {data?.total ?? 0} conversations
            </p>

            {/* Search */}
            <div className="relative mt-3">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search students…"
                className="w-full rounded-lg border border-input bg-background py-1.5 pl-8 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* Status filter */}
            <div className="mt-2 flex items-center gap-1">
              <SlidersHorizontal className="h-3 w-3 text-muted-foreground" />
              {(["", "open", "resolved"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
                    statusFilter === s
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {s === "" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Thread list */}
          <div className="flex-1 space-y-0.5 overflow-y-auto p-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : threads.length === 0 ? (
              <div className="flex flex-col items-center py-16 text-center">
                <MessageSquare className="h-8 w-8 text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">
                  No student feedback yet
                </p>
              </div>
            ) : (
              <AnimatePresence initial={false}>
                {threads.map((t) => (
                  <motion.div
                    key={t.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <ThreadItem
                      thread={t}
                      active={t.id === selectedId}
                      onClick={() => setSelectedId(t.id)}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>
        </div>

        {/* ── Chat panel ─────────────────────────────────────────────────── */}
        <div className="flex flex-1 flex-col">
          <AnimatePresence mode="wait">
            {selectedThread ? (
              <motion.div
                key={selectedThread.id}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="flex h-full"
              >
                <FeedbackChatPanel
                  thread={selectedThread}
                  isAdmin
                  className="flex-1"
                  onResolved={() => {
                    qc.invalidateQueries({ queryKey: queryKeys.feedback.threads() });
                  }}
                />
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex h-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border"
              >
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                  <MessageSquare className="h-8 w-8 text-muted-foreground" />
                </div>
                <p className="mt-4 font-semibold text-foreground">
                  Select a conversation
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Choose a student thread from the left panel
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </AuthGuard>
  );
}
