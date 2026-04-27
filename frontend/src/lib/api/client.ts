import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import axiosRetry from "axios-retry";
import { useAuthStore } from "@/stores/authStore";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Retry on 503 (Render cold-start) — 3 attempts with exponential backoff
axiosRetry(apiClient, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (err) => err.response?.status === 503,
});

// Attach Bearer token on every outgoing request
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 → attempt token refresh → retry original request once
let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

apiClient.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (err.response?.status !== 401 || original._retry) {
      return Promise.reject(err);
    }

    original._retry = true;

    if (isRefreshing) {
      // Queue parallel 401s — they all get resolved when refresh completes
      return new Promise((resolve) => {
        refreshQueue.push((token: string) => {
          original.headers.Authorization = `Bearer ${token}`;
          resolve(apiClient(original));
        });
      });
    }

    isRefreshing = true;

    try {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (!refreshToken) throw new Error("No refresh token available");

      // Use plain axios (not apiClient) to avoid interceptor loop
      const { data } = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
        { refresh_token: refreshToken },
        { headers: { "Content-Type": "application/json" } }
      );

      const { access_token, refresh_token: newRefresh } = data as {
        access_token: string;
        refresh_token: string;
      };

      useAuthStore.getState().setTokens(access_token, newRefresh);

      refreshQueue.forEach((cb) => cb(access_token));
      refreshQueue = [];

      original.headers.Authorization = `Bearer ${access_token}`;
      return apiClient(original);
    } catch {
      // Refresh failed — clear session and redirect to login
      useAuthStore.getState().clearSession();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return Promise.reject(err);
    } finally {
      isRefreshing = false;
    }
  }
);
