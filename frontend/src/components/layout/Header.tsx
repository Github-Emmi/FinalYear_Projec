"use client";

import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { NotificationBell } from "./NotificationBell";
import { logout } from "@/lib/api/auth";
import { useRouter } from "next/navigation";
import {
  Sun, Moon, Monitor, LogOut, ChevronDown,
  Search, Users, GraduationCap, UserCheck,
  Settings, BarChart3, Wifi, Cpu, Brain,
} from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import { useTheme } from "next-themes";
import { Command } from "cmdk";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter as useRouterNav } from "next/navigation";
import { cn } from "@/lib/utils/cn";

// ── Palette items ─────────────────────────────────────────────────────────────
const PALETTE_ITEMS = [
  { group: "Navigation", label: "Users", href: "/admin/users", icon: Users },
  { group: "Navigation", label: "Students", href: "/admin/students", icon: GraduationCap },
  { group: "Navigation", label: "Staff", href: "/admin/staff", icon: UserCheck },
  { group: "Navigation", label: "Analytics", href: "/admin/analytics", icon: BarChart3 },
  { group: "Navigation", label: "Settings", href: "/admin/settings", icon: Settings },
  { group: "Navigation", label: "Timetable", href: "/admin/timetable", icon: BarChart3 },
];

// ── System status indicator ───────────────────────────────────────────────────
function StatusDot({ ok, pulse = false }: { ok: boolean; pulse?: boolean }) {
  return (
    <span className="relative flex h-2 w-2">
      {pulse && ok && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
      )}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", ok ? "bg-emerald-500" : "bg-red-500")} />
    </span>
  );
}

function SystemStatusBar() {
  const [ping, setPing] = useState<number | null>(null);
  const [ok, setOk] = useState(true);

  useEffect(() => {
    const check = async () => {
      const t0 = performance.now();
      try {
        const r = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? ""}/api/v1/health`
        );
        setPing(Math.round(performance.now() - t0));
        setOk(r.ok);
      } catch {
        setOk(false);
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="hidden items-center gap-3 text-xs text-muted-foreground lg:flex">
      <div className="flex items-center gap-1.5">
        <StatusDot ok={ok} pulse />
        <Wifi className="h-3 w-3" />
        <span className={ok ? "text-emerald-500 font-medium" : "text-red-500 font-medium"}>
          API: {ok ? `Online (${ping ?? "…"}ms)` : "Offline"}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <StatusDot ok={true} pulse />
        <Cpu className="h-3 w-3" />
        <span className="font-medium text-emerald-500">Worker: Active</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
        </span>
        <Brain className="h-3 w-3" />
        <span className="font-medium text-blue-500">AI: openrouter/free</span>
      </div>
    </div>
  );
}

// ── Command Palette ───────────────────────────────────────────────────────────
function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const nav = useRouterNav();
  const [query, setQuery] = useState("");

  const runItem = (href: string) => {
    nav.push(href);
    onClose();
    setQuery("");
  };

  const filtered = query.trim()
    ? PALETTE_ITEMS.filter((i) => i.label.toLowerCase().includes(query.toLowerCase()))
    : PALETTE_ITEMS;

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
          <motion.div initial={{ opacity: 0, scale: 0.96, y: -8 }} animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }} transition={{ duration: 0.15 }}
            className="relative z-10 w-full max-w-lg overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
            <Command className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground">
              <div className="flex items-center gap-2 border-b border-border px-4 py-3">
                <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                <Command.Input
                  autoFocus
                  value={query}
                  onValueChange={setQuery}
                  placeholder="Search pages, users, settings…"
                  className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                />
                <kbd className="hidden rounded border border-border bg-muted px-1.5 py-0.5 text-xs text-muted-foreground sm:block">
                  ESC
                </kbd>
              </div>
              <Command.List className="max-h-72 overflow-y-auto p-2">
                <Command.Empty className="py-8 text-center text-sm text-muted-foreground">
                  No results found.
                </Command.Empty>
                <Command.Group heading="Navigation">
                  {filtered.map((item) => {
                    const Icon = item.icon;
                    return (
                      <Command.Item key={item.href} value={item.label}
                        onSelect={() => runItem(item.href)}
                        className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-foreground aria-selected:bg-accent">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        {item.label}
                      </Command.Item>
                    );
                  })}
                </Command.Group>
              </Command.List>
              <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
                <span>↑↓ navigate · Enter select · Esc close</span>
              </div>
            </Command>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// ── Main Header ───────────────────────────────────────────────────────────────
export function Header() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const { setTheme } = useUIStore();
  const { theme, setTheme: setNextTheme } = useTheme();
  const [profileOpen, setProfileOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMounted(true), []);

  // Close profile dropdown on outside click
  useEffect(() => {
    if (!profileOpen) return;
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [profileOpen]);

  // Cmd+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

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
    <>
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />

      <header className="flex h-16 items-center justify-between border-b border-border bg-card/80 px-6 backdrop-blur-md">
        {/* Left: Search trigger */}
        <button
          onClick={() => setCmdOpen(true)}
          className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Search className="h-4 w-4" />
          <span className="hidden sm:block">Search…</span>
          <kbd className="ml-1 hidden rounded border border-border bg-background px-1.5 py-0.5 text-xs sm:block">
            ⌘K
          </kbd>
        </button>

        {/* Center: System status */}
        <SystemStatusBar />

        {/* Right: controls */}
        <div className="flex items-center gap-3">
          {/* Theme */}
          {mounted && (
            <div className="flex items-center gap-1 rounded-lg border border-border p-1">
              <button onClick={() => handleTheme("light")}
                className={cn("rounded p-1 transition-colors", theme === "light" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
                aria-label="Light mode"><Sun className="h-4 w-4" /></button>
              <button onClick={() => handleTheme("system")}
                className={cn("rounded p-1 transition-colors", theme === "system" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
                aria-label="System mode"><Monitor className="h-4 w-4" /></button>
              <button onClick={() => handleTheme("dark")}
                className={cn("rounded p-1 transition-colors", theme === "dark" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
                aria-label="Dark mode"><Moon className="h-4 w-4" /></button>
            </div>
          )}

          {/* Notifications */}
          <NotificationBell />

          {/* Profile */}
          <div className="relative" ref={profileRef}>
            <button onClick={() => setProfileOpen((v) => !v)}
              className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-accent">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                {initials}
              </div>
              <span className="hidden max-w-24 truncate font-medium text-foreground sm:block">
                {user?.first_name}
              </span>
              <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", profileOpen && "rotate-180")} />
            </button>

            <AnimatePresence>
              {profileOpen && (
                <motion.div initial={{ opacity: 0, scale: 0.95, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: -4 }}
                  className="absolute right-0 top-full z-50 mt-1 w-52 overflow-hidden rounded-xl border border-border bg-card shadow-xl">
                  <div className="border-b border-border px-4 py-3">
                    <p className="text-sm font-medium text-foreground">{user?.first_name} {user?.last_name}</p>
                    <p className="text-xs text-muted-foreground">{user?.email}</p>
                  </div>
                  <button onClick={handleLogout}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-red-600 transition-colors hover:bg-red-50 dark:hover:bg-red-900/20">
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </header>
    </>
  );
}

