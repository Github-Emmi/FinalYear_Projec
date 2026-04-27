import { apiClient } from "./client";
import type {
  StaffProfileResponse,
  PaginatedResponse,
} from "@/types/models";

export interface StaffListParams {
  page?: number;
  size?: number;
  department_id?: string;
  search?: string;
  is_active?: boolean;
}

export async function listStaff(
  params: StaffListParams = {}
): Promise<PaginatedResponse<StaffProfileResponse>> {
  const res = await apiClient.get<PaginatedResponse<StaffProfileResponse>>(
    "/staff",
    { params }
  );
  return res.data;
}

export async function getStaffMember(id: string): Promise<StaffProfileResponse> {
  const res = await apiClient.get<StaffProfileResponse>(`/staff/${id}`);
  return res.data;
}

export async function getMyStaffProfile(): Promise<StaffProfileResponse> {
  const res = await apiClient.get<StaffProfileResponse>("/staff/me");
  return res.data;
}

export interface StaffCreatePayload {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  staff_id: string;
  department_id?: string | null;
  designation?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  phone?: string | null;
  address?: string | null;
}

export async function createStaff(
  payload: StaffCreatePayload
): Promise<StaffProfileResponse> {
  const res = await apiClient.post<StaffProfileResponse>("/staff", payload);
  return res.data;
}

export async function updateStaff(
  id: string,
  payload: Partial<StaffCreatePayload>
): Promise<StaffProfileResponse> {
  const res = await apiClient.patch<StaffProfileResponse>(
    `/staff/${id}`,
    payload
  );
  return res.data;
}
