import { apiClient } from "./client";

export interface StaffChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface StaffChatResponse {
  reply: string;
}

export async function sendStaffChatMessage(
  message: string,
  history: StaffChatMessage[] = []
): Promise<StaffChatResponse> {
  const res = await apiClient.post<StaffChatResponse>("/staff/chat", {
    message,
    history,
  });
  return res.data;
}
