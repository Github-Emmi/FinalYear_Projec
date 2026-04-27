"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Users,
  GraduationCap,
  UserCheck,
  School,
  ClipboardList,
  BookOpen,
  Loader2,
  TrendingUp,
} from "lucide-react";
import { queryKeys } from "@/lib/query/keys";
import { getPlatformAnalytics } from "@/lib/api/analytics";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { cn } from "@/lib/utils/cn";

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  delay?: number;
}

function StatCard({ label, value, icon: Icon, color, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      className="rounded-xl border border-border bg-card p-5 shadow-sm"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1.5 text-3xl font-bold text-foreground">{value}</p>
        </div>
        <div className={cn("rounded-lg p-2.5", color)}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </motion.div>
  );
}

export default function AdminDashboard() {
  const { data: analytics, isLoading } = useQuery({
    queryKey: queryKeys.analytics.platform(),
    queryFn: getPlatformAnalytics,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Admin Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Platform overview and key metrics
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Stats grid */}
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Total Users"
                value={analytics?.total_users ?? 0}
                icon={Users}
                color="bg-blue-500"
                delay={0}
              />
              <StatCard
                label="Students"
                value={analytics?.total_students ?? 0}
                icon={GraduationCap}
                color="bg-purple-500"
                delay={0.05}
              />
              <StatCard
                label="Staff"
                value={analytics?.total_staff ?? 0}
                icon={UserCheck}
                color="bg-emerald-500"
                delay={0.1}
              />
              <StatCard
                label="Classrooms"
                value={analytics?.total_classrooms ?? 0}
                icon={School}
                color="bg-orange-500"
                delay={0.15}
              />
              <StatCard
                label="Assignments"
                value={analytics?.total_assignments ?? 0}
                icon={ClipboardList}
                color="bg-pink-500"
                delay={0.2}
              />
              <StatCard
                label="Quizzes"
                value={analytics?.total_quizzes ?? 0}
                icon={BookOpen}
                color="bg-cyan-500"
                delay={0.25}
              />
              <StatCard
                label="Submissions Today"
                value={analytics?.submissions_today ?? 0}
                icon={TrendingUp}
                color="bg-indigo-500"
                delay={0.3}
              />
              <StatCard
                label="Grading Queue"
                value={analytics?.grading_queue ?? 0}
                icon={Loader2}
                color="bg-yellow-500"
                delay={0.35}
              />
            </div>
          </>
        )}
      </div>
    </AuthGuard>
  );
}
