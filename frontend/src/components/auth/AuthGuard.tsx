"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import type { UserRole } from "@/types/models";

interface AuthGuardProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

/**
 * Wraps a page/layout and redirects unauthenticated users to /login.
 * If `allowedRoles` is provided, redirects unauthorised roles to their own
 * dashboard instead of showing the protected content.
 */
export function AuthGuard({ children, allowedRoles }: AuthGuardProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
      router.replace(`/${user.role}`);
    }
  }, [isAuthenticated, user, allowedRoles, router]);

  if (!isAuthenticated) return null;
  if (allowedRoles && user && !allowedRoles.includes(user.role)) return null;

  return <>{children}</>;
}
