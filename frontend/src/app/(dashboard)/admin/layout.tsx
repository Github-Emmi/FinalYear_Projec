import { AdminAIChat } from "@/components/admin/AdminAIChat";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <AdminAIChat />
    </>
  );
}
