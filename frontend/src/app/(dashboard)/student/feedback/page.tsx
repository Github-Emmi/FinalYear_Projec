"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Loader2,
  MessageSquarePlus,
  Plus,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { queryKeys } from "@/lib/query/keys";
import {
  createFeedbackThread,
  listFeedbackThreads,
  type FeedbackThreadResponse,
} from "@/lib/api/feedback";
import { FeedbackChatPanel } from "@/components/feedback/FeedbackChatPanel";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { cn } from "@/lib/utils/cn";
import { formatDistanceToNow } from "date-fns";

// ── New thread form ───────────────────────────────────────────────────────────

function NewThreadModal({ onClose, onCreate }: {
  onClose: () => void;
  onCreate: (id: string) => void;
}) {
  const qc = useQueryClient();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  const mutation = useMutation({
    mutationFn: () => createFeedbackThread({ subject: subject || undefined, body }),
    onSuccess: (thread) => {
      qc.invalidateQueries({ queryKey: queryKeys.feedback.threads() });
      toast.success("Feedback sent to admin");
      onCreate(thread.id);
      onClose();
    },
    onError: () => toast.error("Failed to send feedback"),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        className="relative z-10 w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-xl"
      >
        <button onClick={onClose} className="absolute right-4 top-4 rounded-lg p-1 text-muted-foreground hover:bg-accent">
          <X className="h-4 w-4" />
        </button>
        <h2 className="mb-5 text-lg font-semibold text-foreground">Send Feedback to Admin</h2>
        <form
          onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
          className="space-y-3"
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Subject (optional)
            </label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g. Course material issue"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Message <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Describe your feedback, report an issue, or ask a question…"
              className="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-accent"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || !body.trim()}
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {mutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Send Feedback
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

// ── Thread card ───────────────────────────────────────────────────────────────

function ThreadCard({
  thread,
  active,
  onClick,
}: {
  thread: FeedbackThreadResponse;
  active: boolean;
  onClick: () => void;
}) {
  const hasUnread = thread.unread_by_sender > 0;

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-xl border p-3 text-left transition-all",
        active
          ? "border-primary/50 bg-primary/5 ring-1 ring-primary/20"
          : "border-border hover:border-primary/30 hover:bg-accent",
        hasUnread && !active && "border-l-4 border-l-primary"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className={cn("text-sm", hasUnread ? "font-semibold text-foreground" : "font-medium text-foreground")}>
          {thread.subject ?? "Feedback to Admin"}
        </p>
        <span
          className={cn(
            "shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
            thread.status === "resolved"
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
              : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
          )}
        >
          {thread.status}
        </span>
      </div>
      {thread.last_message && (
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {thread.last_message.is_admin_message ? "Admin: " : "You: "}
          {thread.last_message.body}
        </p>
      )}
      <p className="mt-1.5 text-[10px] text-muted-foreground">
        {formatDistanceToNow(new Date(thread.updated_at), { addSuffix: true })}
        {hasUnread && (
          <span className="ml-2 rounded-full bg-primary px-1.5 py-0.5 text-[9px] text-primary-foreground">
            {thread.unread_by_sender} new
          </span>
        )}
      </p>
    </button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StudentFeedbackPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.feedback.threads({}),
    queryFn: () => listFeedbackThreads({ size: 50 }),
    refetchInterval: 15_000,
  });

  const threads = data?.items ?? [];
  const selectedThread = threads.find((t) => t.id === selectedId) ?? null;

  return (
    <AuthGuard allowedRoles={["student"]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Feedback</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Send messages, reports, and files to the admin
            </p>
          </div>
          <button
            onClick={() => setShowNew(true)}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            New Feedback
          </button>
        </div>

        <div className="flex gap-5" style={{ height: "calc(100vh - 14rem)" }}>
          {/* Thread list */}
          <div className="flex w-72 shrink-0 flex-col gap-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : threads.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center rounded-2xl border-2 border-dashed border-border py-16 text-center"
              >
                <MessageSquarePlus className="h-10 w-10 text-muted-foreground" />
                <p className="mt-3 font-medium text-foreground">No feedback yet</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Click "New Feedback" to start
                </p>
              </motion.div>
            ) : (
              <AnimatePresence initial={false}>
                {threads.map((t) => (
                  <motion.div key={t.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <ThreadCard
                      thread={t}
                      active={t.id === selectedId}
                      onClick={() => setSelectedId(t.id)}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>

          {/* Chat panel */}
          <div className="flex flex-1 flex-col">
            <AnimatePresence mode="wait">
              {selectedThread ? (
                <motion.div
                  key={selectedThread.id}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex h-full"
                >
                  <FeedbackChatPanel
                    thread={selectedThread}
                    isAdmin={false}
                    className="flex-1"
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex h-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border"
                >
                  <MessageSquarePlus className="h-10 w-10 text-muted-foreground" />
                  <p className="mt-3 font-semibold text-foreground">Select a conversation</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Or start a new one
                  </p>
                  <button
                    onClick={() => setShowNew(true)}
                    className="mt-4 flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                  >
                    <Plus className="h-4 w-4" />
                    New Feedback
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* New feedback modal */}
      <AnimatePresence>
        {showNew && (
          <NewThreadModal
            onClose={() => setShowNew(false)}
            onCreate={(id) => setSelectedId(id)}
          />
        )}
      </AnimatePresence>
    </AuthGuard>
  );
}
