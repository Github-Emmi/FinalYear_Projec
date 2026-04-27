import { LoginForm } from "@/components/auth/LoginForm";

export const metadata = {
  title: "Sign in — School LMS",
};

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <LoginForm />
    </div>
  );
}
