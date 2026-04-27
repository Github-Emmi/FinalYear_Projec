"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";

export default function RootPage() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    // Redirect to role-specific dashboard
    const role = user?.role ?? "student";
    router.replace(`/${role}`);
  }, [isAuthenticated, user, router]);

  return null;
}
