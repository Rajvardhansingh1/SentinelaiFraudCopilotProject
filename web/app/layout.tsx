import type { Metadata } from "next";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import { AuthProvider } from "@/lib/auth-context";
import { AppShell } from "@/components/layout/app-shell";

export const metadata: Metadata = {
  title: "SentinelAI + Fraud Copilot",
  description: "SentinelAI red-team playground, receipt review, and eval dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg-base text-text-primary antialiased">
        <AuthProvider>
          <SessionProvider>
            <AppShell>{children}</AppShell>
          </SessionProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
