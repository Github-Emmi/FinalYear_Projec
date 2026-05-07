import { StaffAIChat } from "@/components/staff/StaffAIChat";

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <StaffAIChat />
    </>
  );
}
