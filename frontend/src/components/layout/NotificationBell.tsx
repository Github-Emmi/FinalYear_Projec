"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, Loader2 } from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import { listMyNotifications, markNotificationRead, markAllNotificationsRead } from "@/lib/api/notifications";
import { formatRelative } from "@/lib/utils/dates";
import { cn } from "@/lib/utils/cn";

export function NotificationBell() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.notifications.mine({ is_read: false }),
    queryFn: () => listMyNotifications({ page: 1, size: 10, is_read: false }),
    refetchInterval: 60_000,
  });

  const unreadCount = data?.total ?? 0;

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      setOpen(false);
    },
  });

  const markOneMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = () => setOpen(false);
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, [open]);

  return (
    <div className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="relative rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="absolute right-0 top-12 z-50 w-80 rounded-xl border border-border bg-popover shadow-lg"
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold text-foreground">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllMutation.mutate()}
                disabled={markAllMutation.isPending}
                className="flex items-center gap-1 text-xs text-primary hover:underline"
              >
                {markAllMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Check className="h-3 w-3" />
                )}
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {isLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            )}

            {!isLoading && (!data?.items || data.items.length === 0) && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                All caught up!
              </p>
            )}

            {data?.items?.map((n) => (
              <div
                key={n.id}
                className={cn(
                  "flex cursor-pointer items-start gap-3 border-b border-border px-4 py-3 transition-colors hover:bg-accent",
                  !n.is_read && "bg-primary/5"
                )}
                onClick={() => {
                  if (!n.is_read) markOneMutation.mutate(n.id);
                }}
              >
                {!n.is_read && (
                  <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
                )}
                <div className={cn("flex-1", n.is_read && "ml-5")}>
                  <p className="text-sm font-medium text-foreground">
                    {n.title}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                    {n.message}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatRelative(n.created_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-border px-4 py-2">
            <Link
              href={`/notifications`}
              className="block text-center text-xs text-primary hover:underline"
              onClick={() => setOpen(false)}
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
