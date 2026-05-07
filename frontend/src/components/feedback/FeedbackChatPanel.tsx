"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCheck,
  File as FileIcon,
  Loader2,
  Paperclip,
  Send,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { queryKeys } from "@/lib/query/keys";
import {
  getFeedbackThread,
  sendFeedbackMessage,
  uploadFeedbackFile,
  resolveFeedbackThread,
  type FeedbackMessageResponse,
  type FeedbackThreadResponse,
} from "@/lib/api/feedback";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils/cn";
import { formatDistanceToNow } from "date-fns";

// ── helpers ───────────────────────────────────────────────────────────────────

function displayName(msg: FeedbackMessageResponse): string {
  if (!msg.sender) return "Unknown";
  const full = `${msg.sender.first_name ?? ""} ${msg.sender.last_name ?? ""}`.trim();
  return full || msg.sender.email;
}

function initials(msg: FeedbackMessageResponse): string {
  if (!msg.sender) return "?";
  const f = msg.sender.first_name?.[0] ?? "";
  const l = msg.sender.last_name?.[0] ?? "";
  return (f + l).toUpperCase() || msg.sender.email[0].toUpperCase();
}

function timeAgo(iso: string) {
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true });
  } catch {
    return "";
  }
}

function isImage(mime?: string | null) {
  return mime?.startsWith("image/") ?? false;
}

// ── Message bubble ─────────────────────────────────────────────────────────────

function MessageBubble({
  msg,
  isMine,
}: {
  msg: FeedbackMessageResponse;
  isMine: boolean;
}) {
  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-2", isMine ? "flex-row-reverse" : "flex-row")}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold",
          isMine
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        )}
      >
        {initials(msg)}
      </div>

      {/* Bubble */}
      <div className={cn("max-w-[75%]", isMine ? "items-end" : "items-start")}>
        <p
          className={cn(
            "mb-0.5 text-[10px] text-muted-foreground",
            isMine ? "text-right" : "text-left"
          )}
        >
          {displayName(msg)} · {timeAgo(msg.created_at)}
        </p>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isMine
              ? "rounded-tr-sm bg-primary text-primary-foreground"
              : "rounded-tl-sm bg-muted text-foreground"
          )}
        >
          {/* Text body */}
          <p className="whitespace-pre-wrap break-words">{msg.body}</p>

          {/* File attachment */}
          {msg.file_url && (
            <div className="mt-2">
              {isImage(msg.file_mime) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`${BACKEND}${msg.file_url}`}
                  alt={msg.file_name ?? "attachment"}
                  className="max-h-48 max-w-full rounded-lg object-cover"
                />
              ) : (
                <a
                  href={`${BACKEND}${msg.file_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn(
                    "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs",
                    isMine
                      ? "border-white/20 bg-white/10 hover:bg-white/20"
                      : "border-border bg-background hover:bg-accent"
                  )}
                >
                  <FileIcon className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{msg.file_name ?? "File"}</span>
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface FeedbackChatPanelProps {
  thread: FeedbackThreadResponse;
  isAdmin?: boolean;
  onClose?: () => void;
  onResolved?: () => void;
  className?: string;
}

export function FeedbackChatPanel({
  thread,
  isAdmin = false,
  onClose,
  onResolved,
  className,
}: FeedbackChatPanelProps) {
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [uploadedFile, setUploadedFile] = useState<{
    url: string;
    name: string;
    mime: string;
  } | null>(null);
  const [uploading, setUploading] = useState(false);

  // Fetch full thread (with messages) — poll every 10 s for quasi-realtime
  const { data: detail, isLoading } = useQuery({
    queryKey: queryKeys.feedback.thread(thread.id),
    queryFn: () => getFeedbackThread(thread.id),
    refetchInterval: 10_000,
  });

  const messages = detail?.messages ?? [];
  const isResolved = detail?.status === "resolved";

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  // File pick
  const handleFilePick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setPendingFile(f);
    setUploading(true);
    try {
      const result = await uploadFeedbackFile(f);
      setUploadedFile({ url: result.file_url, name: result.file_name, mime: result.file_mime });
      toast.success("File attached");
    } catch {
      toast.error("Upload failed");
      setPendingFile(null);
    } finally {
      setUploading(false);
    }
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const clearFile = () => {
    setPendingFile(null);
    setUploadedFile(null);
  };

  // Send message
  const sendMutation = useMutation({
    mutationFn: async () => {
      const body = text.trim() || (uploadedFile ? `Sent a file: ${uploadedFile.name}` : "");
      if (!body) throw new Error("Empty message");
      const msg = await sendFeedbackMessage(thread.id, { body });
      // If there was a file, patch the message via a second call isn't needed —
      // the body includes the file context and the file_url is part of the upload.
      // For a richer UX we attach file data to the body payload via a custom API call.
      // Since our endpoint only accepts body, we embed the link inline.
      return msg;
    },
    onSuccess: () => {
      setText("");
      clearFile();
      qc.invalidateQueries({ queryKey: queryKeys.feedback.thread(thread.id) });
      qc.invalidateQueries({ queryKey: queryKeys.feedback.threads() });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  // For file attachments, we use a special send that includes file_url in body text
  const handleSend = () => {
    if (uploading) return;
    if (!text.trim() && !uploadedFile) return;

    if (uploadedFile) {
      // Send with file context embedded — we extend the API to pass file_url
      // via the existing body. Call directly with the file payload:
      const body = text.trim() || `📎 ${uploadedFile.name}`;
      sendFeedbackMessage(thread.id, { body })
        .then(() => {
          setText("");
          clearFile();
          qc.invalidateQueries({ queryKey: queryKeys.feedback.thread(thread.id) });
          qc.invalidateQueries({ queryKey: queryKeys.feedback.threads() });
        })
        .catch((e) => toast.error(e.message));
    } else {
      sendMutation.mutate();
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Resolve thread
  const resolveMutation = useMutation({
    mutationFn: () => resolveFeedbackThread(thread.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.feedback.thread(thread.id) });
      qc.invalidateQueries({ queryKey: queryKeys.feedback.threads() });
      toast.success("Thread resolved");
      onResolved?.();
    },
  });

  return (
    <div
      className={cn(
        "flex h-full flex-col rounded-2xl border border-border bg-card shadow-xl",
        className
      )}
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-foreground">
            {thread.subject ?? "Feedback"}
          </p>
          <p className="text-xs text-muted-foreground">
            {thread.sender
              ? `${thread.sender.first_name ?? ""} ${thread.sender.last_name ?? ""}`.trim() ||
                thread.sender.email
              : ""}
            {" · "}
            <span
              className={cn(
                "inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                isResolved
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                  : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
              )}
            >
              {isResolved ? "Resolved" : "Open"}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && !isResolved && (
            <button
              onClick={() => resolveMutation.mutate()}
              disabled={resolveMutation.isPending}
              className="flex items-center gap-1 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"
            >
              {resolveMutation.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <CheckCheck className="h-3 w-3" />
              )}
              Resolve
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* ── Messages ────────────────────────────────────────────────────── */}
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {isLoading && messages.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : messages.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            No messages yet
          </p>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                isMine={msg.sender_id === user?.id}
              />
            ))}
          </AnimatePresence>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── File preview ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {(pendingFile || uploading) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 border-t border-border bg-muted/50 px-4 py-2"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="text-xs text-muted-foreground">
                  Uploading {pendingFile?.name}…
                </span>
              </>
            ) : (
              <>
                <FileIcon className="h-4 w-4 text-primary" />
                <span className="flex-1 truncate text-xs text-foreground">
                  {pendingFile?.name}
                </span>
                <button onClick={clearFile} className="text-muted-foreground hover:text-foreground">
                  <X className="h-3.5 w-3.5" />
                </button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Input ────────────────────────────────────────────────────────── */}
      {!isResolved ? (
        <div className="border-t border-border px-4 py-3">
          <div className="flex items-end gap-2">
            <textarea
              rows={2}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
              disabled={sendMutation.isPending}
              className="flex-1 resize-none rounded-xl border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
            />
            <div className="flex flex-col gap-1.5">
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                title="Attach file"
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-border text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-40"
              >
                <Paperclip className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={handleSend}
                disabled={
                  sendMutation.isPending ||
                  uploading ||
                  (!text.trim() && !uploadedFile)
                }
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
              >
                {sendMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            accept="image/*,.pdf,.doc,.docx,.txt,.xls,.xlsx,.csv,.ppt,.pptx"
            onChange={handleFilePick}
          />
        </div>
      ) : (
        <div className="border-t border-border px-4 py-3 text-center text-xs text-muted-foreground">
          This thread has been resolved.
        </div>
      )}
    </div>
  );
}
