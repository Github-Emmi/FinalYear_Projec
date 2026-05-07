import { apiClient } from "./client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SenderInfo {
  id: string;
  first_name?: string | null;
  last_name?: string | null;
  email: string;
  role: string;
}

export interface FeedbackMessageResponse {
  id: string;
  created_at: string;
  updated_at: string;
  thread_id: string;
  sender_id: string;
  body: string;
  file_url?: string | null;
  file_name?: string | null;
  file_mime?: string | null;
  is_admin_message: boolean;
  sender?: SenderInfo | null;
}

export interface FeedbackThreadResponse {
  id: string;
  created_at: string;
  updated_at: string;
  sender_id: string;
  sender_role: "student" | "staff";
  subject?: string | null;
  status: "open" | "resolved";
  unread_by_admin: number;
  unread_by_sender: number;
  sender?: SenderInfo | null;
  last_message?: FeedbackMessageResponse | null;
  message_count: number;
}

export interface FeedbackThreadDetail extends FeedbackThreadResponse {
  messages: FeedbackMessageResponse[];
}

export interface FeedbackThreadCreate {
  subject?: string;
  body: string;
}

export interface FeedbackMessageCreate {
  body: string;
}

export interface FeedbackListParams {
  role_filter?: "student" | "staff";
  status?: "open" | "resolved";
  page?: number;
  size?: number;
}

export interface FeedbackListResponse {
  items: FeedbackThreadResponse[];
  total: number;
  page: number;
  size: number;
}

export interface UploadedFile {
  file_url: string;
  file_name: string;
  file_mime: string;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listFeedbackThreads(
  params?: FeedbackListParams
): Promise<FeedbackListResponse> {
  const res = await apiClient.get<FeedbackListResponse>("/feedback/threads", {
    params,
  });
  return res.data;
}

export async function getFeedbackThread(
  threadId: string
): Promise<FeedbackThreadDetail> {
  const res = await apiClient.get<FeedbackThreadDetail>(
    `/feedback/threads/${threadId}`
  );
  return res.data;
}

export async function createFeedbackThread(
  payload: FeedbackThreadCreate
): Promise<FeedbackThreadDetail> {
  const res = await apiClient.post<FeedbackThreadDetail>(
    "/feedback/threads",
    payload
  );
  return res.data;
}

export async function sendFeedbackMessage(
  threadId: string,
  payload: FeedbackMessageCreate
): Promise<FeedbackMessageResponse> {
  const res = await apiClient.post<FeedbackMessageResponse>(
    `/feedback/threads/${threadId}/messages`,
    payload
  );
  return res.data;
}

export async function resolveFeedbackThread(
  threadId: string
): Promise<FeedbackThreadResponse> {
  const res = await apiClient.patch<FeedbackThreadResponse>(
    `/feedback/threads/${threadId}/resolve`
  );
  return res.data;
}

export async function uploadFeedbackFile(
  file: File
): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiClient.post<UploadedFile>("/feedback/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}
