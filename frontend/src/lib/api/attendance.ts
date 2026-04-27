import { apiClient } from "./client";
import type {
  AttendanceRecordResponse,
  AttendanceSummaryResponse,
  PaginatedResponse,
} from "@/types/models";

export interface AttendanceListParams {
  page?: number;
  size?: number;
  classroom_id?: string;
  student_id?: string;
  date_from?: string;
  date_to?: string;
  status?: string;
}

export async function listAttendance(
  params: AttendanceListParams = {}
): Promise<PaginatedResponse<AttendanceRecordResponse>> {
  const res = await apiClient.get<PaginatedResponse<AttendanceRecordResponse>>(
    "/attendance",
    { params }
  );
  return res.data;
}

export async function getAttendanceSummary(params: {
  classroom_id?: string;
  student_id?: string;
  date_from?: string;
  date_to?: string;
}): Promise<AttendanceSummaryResponse[]> {
  const res = await apiClient.get<AttendanceSummaryResponse[]>(
    "/attendance/summary",
    { params }
  );
  return res.data;
}

export interface AttendanceRecordPayload {
  student_id: string;
  classroom_id: string;
  date: string;
  status: "present" | "absent" | "late" | "excused";
  remarks?: string;
}

export async function recordAttendance(
  payload: AttendanceRecordPayload
): Promise<AttendanceRecordResponse> {
  const res = await apiClient.post<AttendanceRecordResponse>(
    "/attendance",
    payload
  );
  return res.data;
}

export async function bulkRecordAttendance(
  records: AttendanceRecordPayload[]
): Promise<AttendanceRecordResponse[]> {
  const res = await apiClient.post<AttendanceRecordResponse[]>(
    "/attendance/bulk",
    { records }
  );
  return res.data;
}
