"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { getMe } from "@/lib/api/auth";
import { queryKeys } from "@/lib/query/keys";

/**
 * Convenience hook that returns the current authenticated user and helpers.
 * Syncs the server-side user record with the Zustand store on mount.
 */
export function useAuth() {
  const { user, isAuthenticated, accessToken, setUser, clearSession } =
    useAuthStore();

  const { isLoading } = useQuery({
    queryKey: queryKeys.auth.me(),
    queryFn: async () => {
      const me = await getMe();
      setUser(me);
      return me;
    },
    enabled: isAuthenticated && !!accessToken,
    staleTime: 5 * 60 * 1000, // 5 min
    retry: false,
  });

  return {
    user,
    isAuthenticated,
    isLoading,
    clearSession,
  };
}
