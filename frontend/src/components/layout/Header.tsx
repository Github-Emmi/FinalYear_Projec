"use client";

import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { NotificationBell } from "./NotificationBell";
import { logout } from "@/lib/api/auth";
import { useRouter } from "next/navigation";
import {
  Sun,
  Moon,
  Monitor,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";
import { useTheme } from "next-themes";

export function Header() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const { setTheme } = useUIStore();
  const { theme, setTheme: setNextTheme } = useTheme();
  const [profileOpen, setProfileOpen] = useState(false);

  const initials = user
    ? `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase()
    : "??";

  const handleTheme = (t: "light" | "dark" | "system") => {
    setTheme(t);
    setNextTheme(t);
  };

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      {/* Page title can be set per-page via slot; header shows app-level controls */}
      <div />

      <div className="flex items-center gap-3">
        {/* Theme switcher */}
        <div className="flex items-center gap-1 rounded-lg border border-border p-1">
          <button
            onClick={() => handleTheme("light")}
            className={`rounded p-1 transition-colors ${theme === "light" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
            aria-label="Light mode"
          >
            <Sun className="h-4 w-4" />
          </button>
          <button
            onClick={() => handleTheme("system")}
            className={`rounded p-1 transition-colors ${theme === "system" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
            aria-label="System mode"
          >
            <Monitor className="h-4 w-4" />
          </button>
          <button
            onClick={() => handleTheme("dark")}
            className={`rounded p-1 transition-colors ${theme === "dark" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
            aria-label="Dark mode"
          >
            <Moon className="h-4 w-4" />
          </button>
        </div>

        <NotificationBell />

        {/* Profile dropdown */}
        <div className="relative">
          <button
            onClick={() => setProfileOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg px-3 py-2 transition-colors hover:bg-accent"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
              {initials}
            </div>
            {user && (
              <div className="hidden text-left sm:block">
                <p className="text-sm font-medium text-foreground">
                  {user.first_name} {user.last_name}
                </p>
                <p className="text-xs capitalize text-muted-foreground">
                  {user.role}
                </p>
              </div>
            )}
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </button>

          {profileOpen && (
            <div className="absolute right-0 top-12 z-50 min-w-[180px] rounded-xl border border-border bg-popover shadow-lg">
              <div className="px-4 py-3">
                <p className="text-sm font-medium text-foreground">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
              <div className="border-t border-border p-1">
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
