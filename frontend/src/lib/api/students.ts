import { apiClient } from "./client";
import type {
  StudentProfileResponse,
  StudentAnalyticsResponse,
  PaginatedResponse,
  AttendanceSummaryResponse,
} from "@/types/models";

export interface StudentListParams {
  page?: number;
  size?: number;
  classroom_id?: string;
  session_year_id?: string;
  search?: string;
  is_active?: boolean;
}

export async function listStudents(
  params: StudentListParams = {}
): Promise<PaginatedResponse<StudentProfileResponse>> {
  const res = await apiClient.get<PaginatedResponse<StudentProfileResponse>>(
    "/students",
    { params }
  );
  return res.data;
}

export async function getStudent(id: string): Promise<StudentProfileResponse> {
  const res = await apiClient.get<StudentProfileResponse>(`/students/${id}`);
  return res.data;
}

export async function getMyStudentProfile(): Promise<StudentProfileResponse> {
  const res = await apiClient.get<StudentProfileResponse>("/students/me");
  return res.data;
}

export async function getStudentAnalytics(
  id: string
): Promise<StudentAnalyticsResponse> {
  const res = await apiClient.get<StudentAnalyticsResponse>(
    `/students/${id}/analytics`
  );
  return res.data;
}

export async function getStudentAttendance(
  id: string
): Promise<AttendanceSummaryResponse> {
  const res = await apiClient.get<AttendanceSummaryResponse>(
    `/students/${id}/attendance`
  );
  return res.data;
}

export interface StudentCreatePayload {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  roll_number: string;
  classroom_id: string;
  session_year_id: string;
  date_of_birth?: string | null;
  gender?: string | null;
  phone?: string | null;
  address?: string | null;
  guardian_name?: string | null;
  guardian_phone?: string | null;
}

export async function createStudent(
  payload: StudentCreatePayload
): Promise<StudentProfileResponse> {
  const res = await apiClient.post<StudentProfileResponse>(
    "/students",
    payload
  );
  return res.data;
}

export async function updateStudent(
  id: string,
  payload: Partial<StudentCreatePayload>
): Promise<StudentProfileResponse> {
  const res = await apiClient.patch<StudentProfileResponse>(
    `/students/${id}`,
    payload
  );
  return res.data;
}

export async function deleteStudent(id: string): Promise<void> {
  await apiClient.delete(`/students/${id}`);
}
