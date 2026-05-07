"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "sonner";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { CommandMenu } from "@/components/layout/CommandMenu";
import { useNotificationStream } from "@/lib/hooks/useNotificationStream";

function DashboardInner({ children }: { children: React.ReactNode }) {
  // Connect the WebSocket notification stream for authenticated users
  useNotificationStream();

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
      <CommandMenu />
      <Toaster richColors closeButton position="top-right" />
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 min
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <DashboardInner>{children}</DashboardInner>
    </QueryClientProvider>
  );
}
