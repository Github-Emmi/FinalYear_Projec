import { apiClient } from "./client";
import type { TokenResponse, UserResponse } from "@/types/models";
import { useAuthStore } from "@/stores/authStore";

/**
 * POST /auth/token — OAuth2 password flow (application/x-www-form-urlencoded)
 * Returns tokens + the authenticated user profile (fetched via GET /auth/me).
 */
export async function login(
  username: string,
  password: string
): Promise<{ tokens: TokenResponse; user: UserResponse }> {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);

  const { data: tokens } = await apiClient.post<TokenResponse>(
    "/auth/token",
    params,
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );

  // Temporarily inject the access token so getMe() can authenticate
  useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);

  const { data: user } = await apiClient.get<UserResponse>("/auth/me");
  return { tokens, user };
}

/**
 * POST /auth/refresh — Exchange refresh token for a new token pair.
 */
export async function refreshTokens(refreshToken: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return data;
}

/**
 * GET /auth/me — Returns the currently authenticated user's profile.
 */
export async function getMe(): Promise<UserResponse> {
  const { data } = await apiClient.get<UserResponse>("/auth/me");
  return data;
}

/**
 * POST /auth/logout — Revokes the refresh token (clears server-side blacklist entry).
 * Also clears local Zustand state.
 */
export async function logout(): Promise<void> {
  try {
    await apiClient.post("/auth/logout");
  } finally {
    useAuthStore.getState().clearSession();
  }
}
