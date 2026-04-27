"use client";

import { useAuthStore } from "@/stores/authStore";
import type { UserRole } from "@/types/models";

/**
 * Returns whether the current user has one of the specified roles.
 */
export function usePermission(allowedRoles: UserRole[]): boolean {
  const role = useAuthStore((s) => s.user?.role);
  if (!role) return false;
  return allowedRoles.includes(role);
}
