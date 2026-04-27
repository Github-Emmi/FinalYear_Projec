"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/authStore";
import { queryKeys } from "@/lib/query/keys";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "";
const PING_INTERVAL_MS = 25_000;

type WSMessageType =
  | "submission:graded"
  | "attempt:graded"
  | "notification:new"
  | "item:update"
  | "pong";

interface WSMessage {
  type: WSMessageType;
  payload?: Record<string, unknown>;
}

/**
 * Maintains a live WebSocket connection to the backend notification stream.
 * Sends a "ping" every 25 s and invalidates relevant TanStack Query caches
 * when grading/notification events arrive.
 *
 * Safe to call at the top of any authenticated layout — it will only connect
 * when `accessToken` is present and will clean up on unmount.
 */
export function useNotificationStream() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !accessToken || !WS_URL) return;

    let isMounted = true;

    function connect() {
      if (!isMounted) return;

      const url = `${WS_URL}?token=${encodeURIComponent(accessToken!)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Start keepalive pings
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (event: MessageEvent<string>) => {
        const raw = event.data;

        // Filter keepalive pongs before attempting JSON parse
        if (raw === "pong") return;

        let msg: WSMessage;
        try {
          msg = JSON.parse(raw) as WSMessage;
        } catch {
          return;
        }

        handleMessage(msg);
      };

      ws.onclose = () => {
        clearPing();
        // Exponential back-off reconnect (max 30 s)
        if (isMounted) {
          reconnectRef.current = setTimeout(connect, Math.min(30_000, 3_000));
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    function handleMessage(msg: WSMessage) {
      switch (msg.type) {
        case "submission:graded": {
          const submissionId = msg.payload?.submission_id as string | undefined;
          const assignmentId = msg.payload?.assignment_id as string | undefined;
          const score = msg.payload?.score as number | undefined;
          const maxScore = msg.payload?.max_score as number | undefined;

          if (submissionId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.assignments.submission(submissionId),
            });
          }
          if (assignmentId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.assignments.submissions(assignmentId),
            });
          }

          const scoreText =
            score !== undefined && maxScore !== undefined
              ? ` — ${score}/${maxScore}`
              : "";
          toast.success(`Assignment graded${scoreText}`);
          break;
        }

        case "attempt:graded": {
          const attemptId = msg.payload?.attempt_id as string | undefined;
          const score = msg.payload?.score as number | undefined;
          const maxScore = msg.payload?.max_score as number | undefined;

          if (attemptId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.quizzes.attempt(attemptId),
            });
          }
          queryClient.invalidateQueries({
            queryKey: queryKeys.quizzes.myAttempts(),
          });

          const scoreText =
            score !== undefined && maxScore !== undefined
              ? ` — ${score}/${maxScore}`
              : "";
          toast.success(`Quiz graded${scoreText}`);
          break;
        }

        case "notification:new": {
          queryClient.invalidateQueries({
            queryKey: queryKeys.notifications.mine(),
          });
          const title = msg.payload?.title as string | undefined;
          if (title) toast.info(title);
          break;
        }

        case "item:update": {
          // Broad invalidation — use sparingly in backend
          queryClient.invalidateQueries();
          break;
        }
      }
    }

    function clearPing() {
      if (pingRef.current) {
        clearInterval(pingRef.current);
        pingRef.current = null;
      }
    }

    connect();

    return () => {
      isMounted = false;
      clearPing();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional teardown
        wsRef.current.close();
      }
    };
  }, [isAuthenticated, accessToken, queryClient]);
}
