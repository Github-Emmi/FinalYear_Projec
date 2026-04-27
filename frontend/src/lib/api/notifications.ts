import { apiClient } from "./client";
import type {
  NotificationResponse,
  PaginatedResponse,
} from "@/types/models";

export interface NotificationListParams {
  page?: number;
  size?: number;
  is_read?: boolean;
}

export async function listMyNotifications(
  params: NotificationListParams = {}
): Promise<PaginatedResponse<NotificationResponse>> {
  const res = await apiClient.get<PaginatedResponse<NotificationResponse>>(
    "/notifications",
    { params }
  );
  return res.data;
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiClient.patch(`/notifications/${id}/read`);
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiClient.post("/notifications/read-all");
}

export async function deleteNotification(id: string): Promise<void> {
  await apiClient.delete(`/notifications/${id}`);
}
