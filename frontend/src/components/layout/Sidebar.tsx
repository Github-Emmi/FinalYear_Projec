"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, Users, BookOpen, ClipboardList, Bell,
  Calendar, BarChart2, Settings, GraduationCap, UserCheck,
  ChevronLeft, ChevronRight, School, CalendarDays, MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import type { UserRole } from "@/types/models";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const adminNav: NavItem[] = [
  { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { label: "Users", href: "/admin/users", icon: Users },
  { label: "Students", href: "/admin/students", icon: GraduationCap },
  { label: "Staff", href: "/admin/staff", icon: UserCheck },
  { label: "Subjects", href: "/admin/subjects", icon: BookOpen },
  { label: "Academic", href: "/admin/academic", icon: School },
  { label: "Timetable", href: "/admin/timetable", icon: CalendarDays },
  { label: "Analytics", href: "/admin/analytics", icon: BarChart2 },
  { label: "Leave", href: "/admin/leave", icon: Calendar },
  { label: "Student Feedback", href: "/admin/feedback/students", icon: MessageSquare },
  { label: "Staff Feedback", href: "/admin/feedback/staff", icon: MessageSquare },
  { label: "Settings", href: "/admin/settings", icon: Settings },
];

const staffNav: NavItem[] = [
  { label: "Dashboard", href: "/staff", icon: LayoutDashboard },
  { label: "Assignments", href: "/staff/assignments", icon: ClipboardList },
  { label: "Quizzes", href: "/staff/quizzes", icon: BookOpen },
  { label: "Attendance", href: "/staff/attendance", icon: UserCheck },
  { label: "Leave", href: "/staff/leave", icon: Calendar },
  { label: "Feedback", href: "/staff/feedback", icon: MessageSquare },
  { label: "Notifications", href: "/staff/notifications", icon: Bell },
];

const studentNav: NavItem[] = [
  { label: "Dashboard", href: "/student", icon: LayoutDashboard },
  { label: "Assignments", href: "/student/assignments", icon: ClipboardList },
  { label: "Quizzes", href: "/student/quizzes", icon: BookOpen },
  { label: "Attendance", href: "/student/attendance", icon: UserCheck },
  { label: "Feedback", href: "/student/feedback", icon: MessageSquare },
  { label: "Notifications", href: "/student/notifications", icon: Bell },
];

const navByRole: Record<UserRole, NavItem[]> = {
  admin: adminNav,
  staff: staffNav,
  student: studentNav,
};

const roleColors: Record<UserRole, { badge: string; dot: string }> = {
  admin: { badge: "bg-purple-500/20 text-purple-400 border-purple-500/30", dot: "bg-purple-400" },
  staff: { badge: "bg-blue-500/20 text-blue-400 border-blue-500/30", dot: "bg-blue-400" },
  student: { badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", dot: "bg-emerald-400" },
};

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const role = user?.role as UserRole | undefined;
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const nav = role ? navByRole[role] : [];
  const colors = role ? roleColors[role] : roleColors.student;
  const initials = user
    ? `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase()
    : "??";

  return (
    <motion.aside
      animate={{ width: sidebarOpen ? 240 : 64 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative flex h-screen flex-col border-r border-border/60 bg-background/60 backdrop-blur-md"
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-border/60 px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <School className="h-5 w-5 text-primary" />
        </div>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }} transition={{ duration: 0.15 }}
              className="ml-3">
              <p className="text-sm font-bold text-foreground">School LMS</p>
              <p className="text-[10px] text-muted-foreground">Management System</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* User profile + role badge */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }} className="overflow-hidden border-b border-border/60 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground shadow">
                {initials}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">
                  {user?.first_name} {user?.last_name}
                </p>
                <div className={cn(
                  "mt-0.5 inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                  colors.badge
                )}>
                  <span className={cn("h-1.5 w-1.5 rounded-full", colors.dot)} />
                  {role}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <ul className="space-y-0.5">
          {nav.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === `/${role}`
                ? pathname === item.href
                : pathname.startsWith(item.href);

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onMouseEnter={() => setHoveredItem(item.href)}
                  onMouseLeave={() => setHoveredItem(null)}
                  className={cn(
                    "relative flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                    isActive
                      ? "bg-primary/10 text-primary shadow-sm"
                      : "text-muted-foreground hover:bg-accent/80 hover:text-accent-foreground"
                  )}
                >
                  {/* Active left bar */}
                  {isActive && (
                    <motion.div layoutId="active-nav-bar"
                      className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                  )}
                  <Icon className="h-[18px] w-[18px] shrink-0" />
                  <AnimatePresence>
                    {sidebarOpen && (
                      <motion.span initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -8 }} transition={{ duration: 0.12 }}
                        className="ml-3 truncate">
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>

                  {/* Tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.href && (
                    <div className="absolute left-14 z-50 whitespace-nowrap rounded-lg border border-border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-lg">
                      {item.label}
                    </div>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={toggleSidebar}
        className="flex h-11 items-center justify-center border-t border-border/60 text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
        aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
      >
        {sidebarOpen ? (
          <ChevronLeft className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
      </button>
    </motion.aside>
  );
}

