import { apiClient } from "./client";
import type {
  LeaveRequestResponse,
  PaginatedResponse,
} from "@/types/models";

export interface LeaveListParams {
  page?: number;
  size?: number;
  status?: string;
  staff_id?: string;
}

export async function listLeaveRequests(
  params: LeaveListParams = {}
): Promise<PaginatedResponse<LeaveRequestResponse>> {
  const res = await apiClient.get<PaginatedResponse<LeaveRequestResponse>>(
    "/leave",
    { params }
  );
  return res.data;
}

export async function getPendingLeaveRequests(): Promise<
  LeaveRequestResponse[]
> {
  const res = await apiClient.get<LeaveRequestResponse[]>("/leave/pending");
  return res.data;
}

export async function getLeaveRequest(id: string): Promise<LeaveRequestResponse> {
  const res = await apiClient.get<LeaveRequestResponse>(`/leave/${id}`);
  return res.data;
}

export interface LeaveCreatePayload {
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
}

export async function createLeaveRequest(
  payload: LeaveCreatePayload
): Promise<LeaveRequestResponse> {
  const res = await apiClient.post<LeaveRequestResponse>("/leave", payload);
  return res.data;
}

export async function approveLeaveRequest(
  id: string
): Promise<LeaveRequestResponse> {
  const res = await apiClient.patch<LeaveRequestResponse>(
    `/leave/${id}/approve`
  );
  return res.data;
}

export async function rejectLeaveRequest(
  id: string,
  reason?: string
): Promise<LeaveRequestResponse> {
  const res = await apiClient.patch<LeaveRequestResponse>(
    `/leave/${id}/reject`,
    { reason }
  );
  return res.data;
}
