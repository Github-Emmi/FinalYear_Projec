import { apiClient } from "./client";
import type {
  UserResponse,
  PaginatedResponse,
} from "@/types/models";

export interface UserListParams {
  page?: number;
  size?: number;
  role?: string;
  search?: string;
  is_active?: boolean;
}

export async function listUsers(
  params: UserListParams = {}
): Promise<PaginatedResponse<UserResponse>> {
  const res = await apiClient.get<PaginatedResponse<UserResponse>>("/users", {
    params,
  });
  return res.data;
}

export async function getUser(id: string): Promise<UserResponse> {
  const res = await apiClient.get<UserResponse>(`/users/${id}`);
  return res.data;
}

export interface UserCreatePayload {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  role: "admin" | "staff" | "student";
}

export async function createUser(
  payload: UserCreatePayload
): Promise<UserResponse> {
  const res = await apiClient.post<UserResponse>("/users", payload);
  return res.data;
}

export async function updateUser(
  id: string,
  payload: Partial<UserCreatePayload>
): Promise<UserResponse> {
  const res = await apiClient.patch<UserResponse>(`/users/${id}`, payload);
  return res.data;
}

export async function deactivateUser(id: string): Promise<void> {
  await apiClient.delete(`/users/${id}`);
}
