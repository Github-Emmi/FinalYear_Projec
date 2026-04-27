"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Users,
  BookOpen,
  ClipboardList,
  Bell,
  Calendar,
  BarChart2,
  Settings,
  GraduationCap,
  UserCheck,
  ChevronLeft,
  ChevronRight,
  School,
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
  { label: "Academic", href: "/admin/academic", icon: School },
  { label: "Analytics", href: "/admin/analytics", icon: BarChart2 },
  { label: "Leave", href: "/admin/leave", icon: Calendar },
  { label: "Settings", href: "/admin/settings", icon: Settings },
];

const staffNav: NavItem[] = [
  { label: "Dashboard", href: "/staff", icon: LayoutDashboard },
  { label: "Assignments", href: "/staff/assignments", icon: ClipboardList },
  { label: "Quizzes", href: "/staff/quizzes", icon: BookOpen },
  { label: "Attendance", href: "/staff/attendance", icon: UserCheck },
  { label: "Leave", href: "/staff/leave", icon: Calendar },
  { label: "Notifications", href: "/staff/notifications", icon: Bell },
];

const studentNav: NavItem[] = [
  { label: "Dashboard", href: "/student", icon: LayoutDashboard },
  { label: "Assignments", href: "/student/assignments", icon: ClipboardList },
  { label: "Quizzes", href: "/student/quizzes", icon: BookOpen },
  { label: "Attendance", href: "/student/attendance", icon: UserCheck },
  { label: "Notifications", href: "/student/notifications", icon: Bell },
];

const navByRole: Record<UserRole, NavItem[]> = {
  admin: adminNav,
  staff: staffNav,
  student: studentNav,
};

export function Sidebar() {
  const pathname = usePathname();
  const role = useAuthStore((s) => s.user?.role);
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const nav = role ? navByRole[role] : [];

  return (
    <motion.aside
      animate={{ width: sidebarOpen ? 240 : 64 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative flex h-screen flex-col border-r border-border bg-card"
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-border px-4">
        <School className="h-7 w-7 shrink-0 text-primary" />
        <AnimatePresence>
          {sidebarOpen && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.15 }}
              className="ml-3 font-semibold text-foreground"
            >
              School LMS
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        <ul className="space-y-1">
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
                    "relative flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  <AnimatePresence>
                    {sidebarOpen && (
                      <motion.span
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -8 }}
                        transition={{ duration: 0.12 }}
                        className="ml-3 truncate"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>

                  {/* Tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.href && (
                    <div className="absolute left-14 z-50 whitespace-nowrap rounded-md border border-border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
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
        className="flex h-12 items-center justify-center border-t border-border text-muted-foreground transition-colors hover:text-foreground"
        aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
      >
        {sidebarOpen ? (
          <ChevronLeft className="h-5 w-5" />
        ) : (
          <ChevronRight className="h-5 w-5" />
        )}
      </button>
    </motion.aside>
  );
}
