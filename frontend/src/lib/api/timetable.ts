import { apiClient } from "./client";

export interface TimetableEntryResponse {
  id: string;
  classroom_id: string;
  subject_id: string;
  staff_id: string;
  session_year_id: string;
  day_of_week: number; // 0=Mon … 6=Sun
  start_time: string;  // "08:00"
  end_time: string;    // "09:00"
  period_number?: number | null;
  notes?: string | null;
  classroom: { id: string; name: string };
  subject: { id: string; name: string };
  staff: { id: string; name: string };
}

export interface TimetableEntryCreate {
  classroom_id: string;
  subject_id: string;
  staff_id: string;
  session_year_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  period_number?: number | null;
  notes?: string | null;
}

export interface TimetableListParams {
  classroom_id?: string;
  session_year_id?: string;
}

interface TimetableListResponse {
  items: TimetableEntryResponse[];
  total: number;
}

export async function listTimetable(params: TimetableListParams = {}): Promise<TimetableListResponse> {
  const res = await apiClient.get<TimetableListResponse>("/academic/timetable", { params });
  return res.data;
}

export async function createTimetableEntry(payload: TimetableEntryCreate): Promise<TimetableEntryResponse> {
  const res = await apiClient.post<TimetableEntryResponse>("/academic/timetable", payload);
  return res.data;
}

export async function updateTimetableEntry(
  id: string,
  payload: Partial<TimetableEntryCreate>
): Promise<TimetableEntryResponse> {
  const res = await apiClient.patch<TimetableEntryResponse>(`/academic/timetable/${id}`, payload);
  return res.data;
}

export async function deleteTimetableEntry(id: string): Promise<void> {
  await apiClient.delete(`/academic/timetable/${id}`);
}
