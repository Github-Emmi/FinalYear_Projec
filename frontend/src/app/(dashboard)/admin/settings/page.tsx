"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { Settings, Bell, Shield, Palette } from "lucide-react";

export default function AdminSettingsPage() {
  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Platform configuration and preferences
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <SettingCard
            icon={<Bell className="h-5 w-5 text-primary" />}
            title="Notifications"
            description="Configure email and in-app notification rules for grading, leave, and announcements."
          />
          <SettingCard
            icon={<Shield className="h-5 w-5 text-primary" />}
            title="Access Control"
            description="Manage role permissions and password policies for all user types."
          />
          <SettingCard
            icon={<Palette className="h-5 w-5 text-primary" />}
            title="Appearance"
            description="Customise the platform theme and branding for your institution."
          />
          <SettingCard
            icon={<Settings className="h-5 w-5 text-primary" />}
            title="General"
            description="Institution name, timezone, academic calendar defaults, and AI grading settings."
          />
        </div>

        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800/40 dark:bg-amber-900/20 dark:text-amber-400">
          Full settings management is coming in a future release. Use the API directly or seed scripts to configure platform options for now.
        </div>
      </div>
    </AuthGuard>
  );
}

function SettingCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
          {icon}
        </div>
        <h3 className="font-semibold text-foreground">{title}</h3>
      </div>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
