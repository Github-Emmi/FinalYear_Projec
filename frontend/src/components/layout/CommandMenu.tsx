"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "cmdk";
import {
  LayoutDashboard,
  Users,
  BookOpen,
  ClipboardList,
  Bell,
  Calendar,
  BarChart2,
  GraduationCap,
  UserCheck,
  LogOut,
  School,
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { logout } from "@/lib/api/auth";

interface CommandEntry {
  label: string;
  icon: React.ElementType;
  href?: string;
  action?: () => void;
  roles: ("admin" | "staff" | "student")[];
}

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const role = useAuthStore((s) => s.user?.role);

  // Cmd/Ctrl + K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const handleLogout = useCallback(async () => {
    setOpen(false);
    await logout();
    router.replace("/login");
  }, [router]);

  const commands: CommandEntry[] = [
    {
      label: "Dashboard",
      icon: LayoutDashboard,
      href: `/${role}`,
      roles: ["admin", "staff", "student"],
    },
    {
      label: "Users",
      icon: Users,
      href: "/admin/users",
      roles: ["admin"],
    },
    {
      label: "Students",
      icon: GraduationCap,
      href: "/admin/students",
      roles: ["admin"],
    },
    {
      label: "Staff",
      icon: UserCheck,
      href: "/admin/staff",
      roles: ["admin"],
    },
    {
      label: "Academic",
      icon: School,
      href: "/admin/academic",
      roles: ["admin"],
    },
    {
      label: "Analytics",
      icon: BarChart2,
      href: "/admin/analytics",
      roles: ["admin"],
    },
    {
      label: "Assignments",
      icon: ClipboardList,
      href: `/${role}/assignments`,
      roles: ["staff", "student"],
    },
    {
      label: "Quizzes",
      icon: BookOpen,
      href: `/${role}/quizzes`,
      roles: ["staff", "student"],
    },
    {
      label: "Attendance",
      icon: UserCheck,
      href: `/${role}/attendance`,
      roles: ["staff", "student"],
    },
    {
      label: "Leave",
      icon: Calendar,
      href: `/${role}/leave`,
      roles: ["admin", "staff"],
    },
    {
      label: "Notifications",
      icon: Bell,
      href: `/${role}/notifications`,
      roles: ["admin", "staff", "student"],
    },
    {
      label: "Sign out",
      icon: LogOut,
      action: handleLogout,
      roles: ["admin", "staff", "student"],
    },
  ];

  const filtered = role
    ? commands.filter((c) => c.roles.includes(role))
    : [];

  const navigate = (entry: CommandEntry) => {
    setOpen(false);
    if (entry.action) {
      entry.action();
    } else if (entry.href) {
      router.push(entry.href);
    }
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {filtered
            .filter((c) => !c.action)
            .map((entry) => {
              const Icon = entry.icon;
              return (
                <CommandItem
                  key={entry.label}
                  onSelect={() => navigate(entry)}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {entry.label}
                </CommandItem>
              );
            })}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Actions">
          {filtered
            .filter((c) => !!c.action)
            .map((entry) => {
              const Icon = entry.icon;
              return (
                <CommandItem
                  key={entry.label}
                  onSelect={() => navigate(entry)}
                  className="text-destructive"
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {entry.label}
                </CommandItem>
              );
            })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
