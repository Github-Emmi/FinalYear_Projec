import { apiClient } from "./client";
import type {
  ClassroomAnalyticsResponse,
  PlatformAnalyticsResponse,
  StaffAnalyticsResponse,
} from "@/types/models";

export async function getClassroomAnalytics(
  classroomId: string
): Promise<ClassroomAnalyticsResponse> {
  const res = await apiClient.get<ClassroomAnalyticsResponse>(
    `/analytics/classrooms/${classroomId}`
  );
  return res.data;
}

export async function getPlatformAnalytics(): Promise<PlatformAnalyticsResponse> {
  const res = await apiClient.get<PlatformAnalyticsResponse>(
    "/analytics/platform"
  );
  return res.data;
}

export async function getStaffAnalytics(
  staffId: string
): Promise<StaffAnalyticsResponse> {
  const res = await apiClient.get<StaffAnalyticsResponse>(
    `/analytics/staff/${staffId}`
  );
  return res.data;
}
