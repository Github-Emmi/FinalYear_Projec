"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, Loader2 } from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import {
  listMyNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api/notifications";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { formatRelative } from "@/lib/utils/dates";
import { cn } from "@/lib/utils/cn";
import { toast } from "sonner";

export default function NotificationsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.notifications.mine({ page: 1, size: 50 }),
    queryFn: () => listMyNotifications({ page: 1, size: 50 }),
  });

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("All marked as read");
    },
  });

  const markOneMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const unread = data?.items.filter((n) => !n.is_read).length ?? 0;

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Notifications
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {unread > 0 ? `${unread} unread` : "All caught up"}
            </p>
          </div>
          {unread > 0 && (
            <button
              onClick={() => markAllMutation.mutate()}
              disabled={markAllMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-muted px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent disabled:opacity-60"
            >
              {markAllMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCheck className="h-4 w-4" />
              )}
              Mark all as read
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-card shadow-sm divide-y divide-border">
            {(!data?.items || data.items.length === 0) && (
              <div className="flex flex-col items-center py-12">
                <Bell className="mb-3 h-8 w-8 text-muted-foreground" />
                <p className="text-muted-foreground">No notifications</p>
              </div>
            )}
            {data?.items.map((n) => (
              <div
                key={n.id}
                onClick={() => {
                  if (!n.is_read) markOneMutation.mutate(n.id);
                }}
                className={cn(
                  "flex cursor-pointer items-start gap-4 px-5 py-4 transition-colors hover:bg-accent",
                  !n.is_read && "bg-primary/5"
                )}
              >
                {!n.is_read && (
                  <div className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary" />
                )}
                <div className={cn("flex-1", n.is_read && "ml-6")}>
                  <p className="font-medium text-foreground">{n.title}</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {n.message}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatRelative(n.created_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
