import { apiClient } from "./client";
import type {
  QuizResponse,
  QuizQuestionResponse,
  QuizAttemptResponse,
  PaginatedResponse,
} from "@/types/models";

export interface QuizListParams {
  page?: number;
  size?: number;
  subject_id?: string;
  is_published?: boolean;
}

export async function listQuizzes(
  params: QuizListParams = {}
): Promise<PaginatedResponse<QuizResponse>> {
  const res = await apiClient.get<PaginatedResponse<QuizResponse>>(
    "/quizzes",
    { params }
  );
  return res.data;
}

export async function getQuiz(id: string): Promise<QuizResponse> {
  const res = await apiClient.get<QuizResponse>(`/quizzes/${id}`);
  return res.data;
}

export async function getQuizQuestions(
  quizId: string
): Promise<QuizQuestionResponse[]> {
  const res = await apiClient.get<QuizQuestionResponse[]>(
    `/quizzes/${quizId}/questions`
  );
  return res.data;
}

export interface QuizCreatePayload {
  title: string;
  description?: string;
  subject_id: string;
  time_limit_minutes?: number | null;
  max_attempts?: number;
  is_published?: boolean;
}

export async function createQuiz(
  payload: QuizCreatePayload
): Promise<QuizResponse> {
  const res = await apiClient.post<QuizResponse>(
    "/quizzes",
    payload
  );
  return res.data;
}

export async function updateQuiz(
  id: string,
  payload: Partial<QuizCreatePayload>
): Promise<QuizResponse> {
  const res = await apiClient.patch<QuizResponse>(
    `/quizzes/${id}`,
    payload
  );
  return res.data;
}

// ── Attempts ──────────────────────────────────────────────────────────────────

export async function startQuizAttempt(
  quizId: string
): Promise<QuizAttemptResponse> {
  const res = await apiClient.post<QuizAttemptResponse>(
    `/quizzes/${quizId}/attempt`
  );
  return res.data;
}

export async function submitQuizAttempt(
  attemptId: string,
  answers: Record<string, string>
): Promise<QuizAttemptResponse> {
  const res = await apiClient.post<QuizAttemptResponse>(
    `/quizzes/attempts/${attemptId}/submit`,
    { answers }
  );
  return res.data;
}

export async function getAttempt(id: string): Promise<QuizAttemptResponse> {
  const res = await apiClient.get<QuizAttemptResponse>(
    `/quizzes/attempts/${id}`
  );
  return res.data;
}

export async function getMyAttempts(): Promise<QuizAttemptResponse[]> {
  const res = await apiClient.get<QuizAttemptResponse[]>(
    "/quizzes/attempts/mine"
  );
  return res.data;
}
