import { apiClient } from "./client";
import type {
  AssignmentResponse,
  SubmissionResponse,
  PaginatedResponse,
} from "@/types/models";

export interface AssignmentListParams {
  page?: number;
  size?: number;
  subject_id?: string;
  status?: string;
  search?: string;
}

export async function listAssignments(
  params: AssignmentListParams = {}
): Promise<PaginatedResponse<AssignmentResponse>> {
  const res = await apiClient.get<PaginatedResponse<AssignmentResponse>>(
    "/assignments",
    { params }
  );
  return res.data;
}

export async function getAssignment(id: string): Promise<AssignmentResponse> {
  const res = await apiClient.get<AssignmentResponse>(`/assignments/${id}`);
  return res.data;
}

export interface AssignmentCreatePayload {
  title: string;
  description?: string;
  subject_id: string;
  due_date: string;
  max_score?: number;
  allow_late?: boolean;
}

export async function createAssignment(
  payload: AssignmentCreatePayload
): Promise<AssignmentResponse> {
  const res = await apiClient.post<AssignmentResponse>("/assignments", payload);
  return res.data;
}

export async function updateAssignment(
  id: string,
  payload: Partial<AssignmentCreatePayload> & { status?: string }
): Promise<AssignmentResponse> {
  const res = await apiClient.patch<AssignmentResponse>(
    `/assignments/${id}`,
    payload
  );
  return res.data;
}

export async function deleteAssignment(id: string): Promise<void> {
  await apiClient.delete(`/assignments/${id}`);
}

// ── Submissions ───────────────────────────────────────────────────────────────

export async function listSubmissions(
  assignmentId: string
): Promise<SubmissionResponse[]> {
  const res = await apiClient.get<SubmissionResponse[]>(
    `/assignments/${assignmentId}/submissions`
  );
  return res.data;
}

export async function getSubmission(id: string): Promise<SubmissionResponse> {
  const res = await apiClient.get<SubmissionResponse>(
    `/assignments/submissions/${id}`
  );
  return res.data;
}

export async function submitAssignment(
  assignmentId: string,
  content: string
): Promise<SubmissionResponse> {
  const res = await apiClient.post<SubmissionResponse>(
    `/assignments/${assignmentId}/submit`,
    { content }
  );
  return res.data;
}

export async function triggerAIGrading(submissionId: string): Promise<void> {
  await apiClient.post(`/assignments/submissions/${submissionId}/grade`);
}
