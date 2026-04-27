import { apiClient } from "./client";
import type {
  DepartmentResponse,
  ClassRoomResponse,
  SubjectResponse,
  SessionYearResponse,
  PaginatedResponse,
} from "@/types/models";

// ── Departments ───────────────────────────────────────────────────────────────

export async function listDepartments(): Promise<DepartmentResponse[]> {
  const res = await apiClient.get<DepartmentResponse[]>("/academic/departments");
  return res.data;
}

export async function getDepartment(id: string): Promise<DepartmentResponse> {
  const res = await apiClient.get<DepartmentResponse>(
    `/academic/departments/${id}`
  );
  return res.data;
}

export async function createDepartment(payload: {
  name: string;
  code: string;
  description?: string;
}): Promise<DepartmentResponse> {
  const res = await apiClient.post<DepartmentResponse>(
    "/academic/departments",
    payload
  );
  return res.data;
}

// ── ClassRooms ────────────────────────────────────────────────────────────────

export interface ClassroomListParams {
  page?: number;
  size?: number;
  department_id?: string;
  academic_year?: string;
}

export async function listClassrooms(
  params: ClassroomListParams = {}
): Promise<PaginatedResponse<ClassRoomResponse>> {
  const res = await apiClient.get<PaginatedResponse<ClassRoomResponse>>(
    "/academic/classrooms",
    { params }
  );
  return res.data;
}

export async function getClassroom(id: string): Promise<ClassRoomResponse> {
  const res = await apiClient.get<ClassRoomResponse>(
    `/academic/classrooms/${id}`
  );
  return res.data;
}

export async function createClassroom(payload: {
  name: string;
  grade_level: number;
  section: string;
  department_id: string;
  academic_year: string;
}): Promise<ClassRoomResponse> {
  const res = await apiClient.post<ClassRoomResponse>(
    "/academic/classrooms",
    payload
  );
  return res.data;
}

// ── Subjects ──────────────────────────────────────────────────────────────────

export interface SubjectListParams {
  page?: number;
  size?: number;
  classroom_id?: string;
}

export async function listSubjects(
  params: SubjectListParams = {}
): Promise<PaginatedResponse<SubjectResponse>> {
  const res = await apiClient.get<PaginatedResponse<SubjectResponse>>(
    "/academic/subjects",
    { params }
  );
  return res.data;
}

export async function getSubject(id: string): Promise<SubjectResponse> {
  const res = await apiClient.get<SubjectResponse>(`/academic/subjects/${id}`);
  return res.data;
}

export async function createSubject(payload: {
  name: string;
  code: string;
  classroom_id: string;
}): Promise<SubjectResponse> {
  const res = await apiClient.post<SubjectResponse>(
    "/academic/subjects",
    payload
  );
  return res.data;
}

// ── Session Years ─────────────────────────────────────────────────────────────

export async function listSessionYears(): Promise<SessionYearResponse[]> {
  const res = await apiClient.get<SessionYearResponse[]>(
    "/academic/session-years"
  );
  return res.data;
}

export async function createSessionYear(payload: {
  start_year: number;
  end_year: number;
  is_current?: boolean;
}): Promise<SessionYearResponse> {
  const res = await apiClient.post<SessionYearResponse>(
    "/academic/session-years",
    payload
  );
  return res.data;
}
